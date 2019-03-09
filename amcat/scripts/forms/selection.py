# ##########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################


import datetime
import hashlib
import itertools
import json
import logging
from itertools import filterfalse

from django import forms
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ValidationError
from django.db.models import Model
from django.db.models.query import QuerySet

from amcat.forms.forms import order_fields
from amcat.models import Codebook, Language, Article, ArticleSet, CodingJob, CodingSchemaField, Code, \
    CodebookCode, CodingSchema
from amcat.models.coding.codingschemafield import FIELDTYPE_IDS
from amcat.tools import aggregate_es, aggregate_orm
from amcat.tools.amcates import get_property_mapping_type
from amcat.tools.djangotoolkit import db_supports_distinct_on
from amcat.tools.keywordsearch import SelectionSearch
from amcat.tools.toolkit import to_datetime

log = logging.getLogger(__name__)

DATETYPES = {
    "all": "All Dates",
    "on": "On",
    "before": "Before",
    "after": "After",
    "between": "Between",
    "relative": "Relative"
}

__all__ = [
    "SelectionForm",
    "ModelMultipleChoiceFieldWithIdLabel",
    "ModelChoiceFieldWithIdLabel"
]

DAY_DELTA = datetime.timedelta(hours=23, minutes=59, seconds=59, milliseconds=999)


class ModelMultipleChoiceFieldWithIdLabel(forms.ModelMultipleChoiceField):
    def clean(self, value):
        # HACK / WORKAROUND: For reasons unbeknown to me, value sometimes is
        # a list of None's. This seems silly, so we filter them.
        if value is not None:
            value = [v for v in value if v is not None]
        return super(ModelMultipleChoiceFieldWithIdLabel, self).clean(value)

    def label_from_instance(self, obj):
        return "%s - %s" % (obj.id, getattr(obj, obj.__label__))


class ModelChoiceFieldWithIdLabel(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return "%s - %s" % (obj.id, obj)


def _add_to_dict(dict, key, value):
    if hasattr(dict, "getlist") and isinstance(value, (list, tuple)):
        return dict.setlist(key, value)
    dict[key] = value


def get_all_schemafields(codingjobs):
    codingjobs = CodingJob.objects.filter(id__in=[c.id for c in codingjobs])
    codingschema_ids = codingjobs.values_list("unitschema_id", "articleschema_id")
    codingschema_ids = set(itertools.chain.from_iterable(codingschema_ids))
    codingschemas = CodingSchema.objects.filter(id__in=codingschema_ids)
    return CodingSchemaField.objects.filter(codingschema__in=codingschemas)


def prepare(value):
    if isinstance(value, (list, tuple, set, QuerySet)):
        return sorted(map(prepare, value))
    elif isinstance(value, Model):
        return value.id
    elif isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    elif isinstance(value, (int, bool, float, str)):
        return value
    elif isinstance(value, (aggregate_orm.Category, aggregate_orm.Value, aggregate_es.Category, Filter)):
        return repr(value)
    elif value is None:
        return value

    raise ValueError("Could not prepare {} of type {} for serialization".format(value, type(value)))


class TimeDeltaSecondsField(forms.IntegerField):
    """
    A timedelta represented as a number of seconds.
    """
    def clean(self, value):
        seconds = super().clean(value)
        if seconds is not None:
            return datetime.timedelta(seconds=seconds)


class Filter:
    def __init__(self, field, value):
        self.field = field
        self.value = value

    def get_filter_kwargs(self):
        t = get_property_mapping_type(self.field)
        field = self.field

        # filter on .raw to match the whole keyword, rather than phrases.
        # e.g. {"medium": "Die Presse"} must not include {"medium": "Die Presse am Sonntag"}
        if t == "default":
            field = "{}.raw".format(self.field)

        yield field, self.value

    @classmethod
    def clean(cls, field, value, field_types):
        if get_property_mapping_type(field) not in field_types:
            raise ValidationError("Cannot filter on field type: {}".format(get_property_mapping_type(field)))
        try:
            value = prepare(value)
        except ValueError:
            raise ValidationError("Invalid value")
        return cls(field, value)

    def __repr__(self):
        return "{}({},{})".format(self.__class__.__name__, repr(self.field), repr(self.value))

class FiltersField(forms.Field):
    filterable_field_types = ["default", "int", "num", "tag", "url", "id"]

    def __init__(self, fields=(), **kwargs):
        super().__init__(**kwargs)
        self._fields = ()
        self.fields = fields

    @property
    def fields(self):
        return self._fields

    @fields.setter
    def fields(self, fields):
        self._fields = [f for f in fields if get_property_mapping_type(f) in self.filterable_field_types]
        self.initial = ",".join(self._fields)

    def validate(self, value):
        super().validate(value)
        if value in self.empty_values:  # the super call handles the 'required' kwarg
            return
        if not isinstance(value, dict) or not all(
                                isinstance(k, str) and isinstance(vs, list) and all(
                    isinstance(v, (str, int, float)) for v in vs) for k, vs in value.items()):
            raise ValidationError("Couldn't parse JSON: Root element should be a {str: (str|int|float)[]} mapping.")

    def to_python(self, value):
        if value in self.empty_values:
            return
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError("Couldn't parse JSON: invalid JSON")

    def clean(self, value):
        fielddict = super().clean(value)
        if fielddict in self.empty_values:
            return

        value = []
        for k, v in fielddict.items():
            value.append(Filter.clean(k, v, field_types=self.filterable_field_types))
        return value


@order_fields()
class SelectionForm(forms.Form):
    include_all = forms.BooleanField(label="Include articles not matched by any keyword", required=False, initial=False)
    articlesets = ModelMultipleChoiceFieldWithIdLabel(queryset=ArticleSet.objects.none(), required=False, initial=())
    codingjobs = ModelMultipleChoiceFieldWithIdLabel(queryset=CodingJob.objects.none(), required=False, initial=())
    article_ids = forms.CharField(widget=forms.Textarea, required=False)

    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)
    on_date = forms.DateField(required=False)
    relative_date = TimeDeltaSecondsField(required=False, min_value=-2**63, max_value=0)
    datetype = forms.ChoiceField(choices=DATETYPES.items(), initial='all', required=True)

    filters = FiltersField(required=False)

    codebook_replacement_language = ModelChoiceFieldWithIdLabel(queryset=Language.objects.all(), required=False,
                                                                label="Language which is used to replace keywords")
    codebook_label_language = ModelChoiceFieldWithIdLabel(queryset=Language.objects.all(), required=False,
                                                          label="Language for keywords")
    codebook = ModelChoiceFieldWithIdLabel(queryset=Codebook.objects.all(), required=False, label="Use Codebook")

    query = forms.CharField(widget=forms.Textarea, required=False)

    codingschemafield_1 = ModelChoiceFieldWithIdLabel(queryset=CodingSchemaField.objects.none(), required=False)
    codingschemafield_value_1 = ModelMultipleChoiceFieldWithIdLabel(queryset=Code.objects.none(), required=False)
    codingschemafield_include_descendants_1 = forms.BooleanField(required=False)

    # Because hack > not at all?
    codingschemafield_2 = ModelChoiceFieldWithIdLabel(queryset=CodingSchemaField.objects.none(), required=False)
    codingschemafield_value_2 = ModelMultipleChoiceFieldWithIdLabel(queryset=Code.objects.none(), required=False)
    codingschemafield_include_descendants_2 = forms.BooleanField(required=False)

    codingschemafield_3 = ModelChoiceFieldWithIdLabel(queryset=CodingSchemaField.objects.none(), required=False)
    codingschemafield_value_3 = ModelMultipleChoiceFieldWithIdLabel(queryset=Code.objects.none(), required=False)
    codingschemafield_include_descendants_3 = forms.BooleanField(required=False)

    codingschemafield_match_condition = forms.ChoiceField(
        label="Must match filters",
        required=True,
        initial="ALL",
        choices=(("ANY", "Any"), ("ALL", "All"))
    )

    def __init__(self, project=None, articlesets=None, codingjobs=None, data=None, *args, **kwargs):
        """
        @param codingojobs: when specified,

        @param project: project to generate this form for
        @type project: amcat.models.Project

        @param articlesets: determines limitation of articlesets
        @type articlesets: django.db.QuerySet
        """
        super(SelectionForm, self).__init__(data, *args, **kwargs)

        if articlesets is None:
            articlesets = project.all_articlesets(distinct=True)

        self.project = project
        self.articlesets = articlesets
        self.codingjobs = codingjobs if codingjobs is not None else CodingJob.objects.none()
        self.schemafields = None

        self.fields['articlesets'].queryset = articlesets.order_by('-pk')
        self.fields['codebook'].queryset = project.get_codebooks()
        self.fields['codingjobs'].queryset = project.codingjob_set.filter(id__in=self.codingjobs)
        self.fields['codebook_label_language'].queryset = self.fields['codebook_replacement_language'].queryset = (
            Language.objects.filter(labels__code__codebook_codes__codebook__in=project.get_codebooks()).distinct()
        )

        if self.codingjobs:
            self.fields['articlesets'].queryset = self.fields['articlesets'].queryset.filter(
                id__in=codingjobs.values_list("articleset_id", flat=True)
            )

            self.schemafields = get_all_schemafields(self.codingjobs)

            schemafields_codebooks = self.schemafields.filter(fieldtype__id=FIELDTYPE_IDS.CODEBOOK).order_by("id")
            schemafield_codebook_ids = schemafields_codebooks.values_list("codebook_id", flat=True)
            codebookcodes = CodebookCode.objects.filter(codebook__id__in=schemafield_codebook_ids)
            codes = Code.objects.filter(id__in=codebookcodes.values_list("code_id", flat=True)).order_by("id")

            fields = {field.id: field for field in self.schemafields}
            choices = [(None, "------")]
            for schema in CodingSchema.objects.filter(fields__in=self.schemafields).values('name').annotate(fields=ArrayAgg('fields')):
                choice_ids = (fields[id] for id in schema['fields'])
                group_choices = tuple((obj.id, "%s - %s" % (obj.id, obj)) for obj in choice_ids)
                choices.append((schema['name'], group_choices))

            for field_name in ("1", "2", "3"):
                self.fields["codingschemafield_{}".format(field_name)].queryset = schemafields_codebooks
                self.fields["codingschemafield_{}".format(field_name)].choices = choices

                self.fields["codingschemafield_value_{}".format(field_name)].widget.attrs = {
                    "class": "depends",
                    "data-depends-on": json.dumps(["codingschemafield_{}".format(field_name), "project"]),
                    "data-depends-url": "/api/v4/projects/{project}/codebooks/{codebook}/?format=json",
                    "data-depends-value": "{code}",
                    "data-depends-label": "{code} - {label}",
                }

            if data is not None:
                for field_name in ("1", "2", "3"):
                    if data.get("codingschemafield_{}".format(field_name)) is not None:
                        try:
                            field_id = int(data["codingschemafield_{}".format(field_name)])
                            field = CodingSchemaField.objects.get(pk=field_id)
                        except ValueError:
                            continue
                        self.fields["codingschemafield_value_{}".format(field_name)].queryset = field.codebook.codes


        if data is not None:
            self.data = self.get_data()

        self.set_filter_fields()



    def get_hash(self, ignore_fields=()) -> str:
        """
        Calculate a hash based on current form. Form *must* be cleaned and valid before executing
        this method. Method returns a SHA256 hexdigest.
        If a relative date is included in the form, it is converted to an absolute date before hashing.
        """
        assert self.is_valid(), "Can only calculate hash for valid forms."
        hash_fields = (fname for fname in self.cleaned_data.keys() if fname not in ignore_fields)
        cleaned_data = [(fname, prepare(self.cleaned_data[fname])) for fname in hash_fields]
        cleaned_data = json.dumps(sorted(cleaned_data)).encode("utf-8")
        return hashlib.sha256(cleaned_data).hexdigest()


    def get_data(self):
        """Include initials in form-data."""
        data = self.data.copy()

        for field_name, value in self.initial.items():
            if field_name not in data:
                _add_to_dict(data, field_name, value)

        for field_name, field in self.fields.items():
            if field_name not in data:
                _add_to_dict(data, field_name, field.initial)
        return data

    def get_date_range(self):
        """
        Calculates and returns a tuple start_date, end_date based on the datetype and date form entries.
        If end_date or start_date is not applicable, it is returned as None
        """
        if 'datetype' not in self.cleaned_data:
            return None, None
        datetype = self.cleaned_data['datetype']

        start_date, end_date = None, None

        try:
            if datetype == "between":
                start_date = self.cleaned_data["start_date"]
                end_date = self.cleaned_data["end_date"]
            elif datetype == "before":
                end_date = self.cleaned_data["end_date"]
            elif datetype == "after":
                start_date = self.cleaned_data["start_date"]
            elif datetype == "on":
                start_date = self.cleaned_data["on_date"]
                end_date = self.cleaned_data["on_date"] + DAY_DELTA
            elif datetype == "relative":
                start_date, end_date = self.cleaned_data["relative_date"]

        except (KeyError, TypeError) as e:
            raise ValidationError("Expected datetype: {}".format(datetype))

        return start_date, end_date

    def clean_codebook_label_language(self):
        return self.cleaned_data.get("codebook_label_language")

    def clean_codebook_replacement_language(self):
        return self.cleaned_data.get("codebook_replacement_language")

    def clean_codebook(self):
        codebook = self.cleaned_data["codebook"]
        label_language = self.cleaned_data["codebook_label_language"]
        replacement_language = self.cleaned_data["codebook_replacement_language"]

        if codebook and not (label_language and replacement_language):
            raise ValidationError(
                "Along with a codebook, you must also select languages.",
                code="missing"
            )

        return codebook

    def clean_datetype(self):
        datetype = self.cleaned_data["datetype"]

        try:
            start_date = self.cleaned_data["start_date"]
            end_date = self.cleaned_data["end_date"]
        except KeyError:
            # start or end date invalid
            return

        if datetype == "between":
            if not (start_date and end_date):
                raise ValidationError("Both a start and an end date need to be defined when datetype is 'between'",
                                      code="missing")
            if end_date and not (start_date < end_date):
                raise ValidationError("End date should be greater than start date")

        elif datetype == "before" and not end_date:
            raise ValidationError("End date should be defined when 'datetype' is 'before'", code="missing")
        elif datetype == "after" and not start_date:
            raise ValidationError("Start date should be defined when 'datetype' is 'after'", code="missing")

        return datetype

    def clean_start_date(self):
        if self.cleaned_data["start_date"]:
            return to_datetime(self.cleaned_data["start_date"])

    def clean_end_date(self):
        if self.cleaned_data["end_date"]:
            return to_datetime(self.cleaned_data["end_date"])

    def clean_on_date(self):
        on_date = self.cleaned_data["on_date"]
        if on_date:
            on_date = to_datetime(on_date)

        return on_date

    def clean_relative_date(self):
        """
        Returns a tuple start_date, end_date, representing the date range
        from (today + N seconds) to today.
        """
        if self.cleaned_data['relative_date']:
            today = to_datetime(datetime.datetime.now())
            delta = self.cleaned_data['relative_date']
            from_date = today + delta
            return to_datetime(from_date), today

    def clean_articlesets(self):
        if not self.cleaned_data["articlesets"]:
            return self.project.all_articlesets()
        return self.cleaned_data["articlesets"]

    def clean_article_ids(self):
        if self._errors:
            return
        article_ids = self.cleaned_data["article_ids"].split("\n")
        article_ids = list(filter(bool, map(str.strip, article_ids)))

        # Parse all article ids as integer
        try:
            article_ids = list(map(int, article_ids))
        except ValueError:
            offender = repr(next(filterfalse(str.isnumeric, article_ids)))
            raise ValidationError("{offender} is not an integer".format(**locals()))

        # Check if they can be chosen
        articlesets = self.cleaned_data["articlesets"]
        distinct_args = ["id"] if db_supports_distinct_on() else []
        all_articles = Article.objects.filter(articlesets_set__in=articlesets).distinct(*distinct_args)
        chosen_articles = Article.objects.filter(id__in=article_ids).distinct(*distinct_args)
        intersection = all_articles & chosen_articles

        if chosen_articles.count() != intersection.count():
            # Find offenders (skipping non-existing, which we can only find when
            # fetching all possible articles)
            existing = all_articles.values_list("id", flat=True)
            offenders = chosen_articles.exclude(id__in=existing).values_list("id", flat=True)
            error_msg = "Article(s) {} do not exist in chosen article sets"
            raise ValidationError((error_msg.format(", ".join(map(str, offenders)))), code="invalid")

        return article_ids

    def clean(self):
        # This is a bit of a hack. We need all the other fields to be correclty validated
        # in order to validate the query field.
        SelectionSearch(self).get_query()
        return self.cleaned_data


    def set_filter_fields(self):
        fields = set()
        for aset in self.articlesets:
            fields |= aset.get_used_properties()
        for aset in ArticleSet.objects.filter(codingjob_set__in=self.codingjobs):
            fields |= aset.get_used_properties()

        self.fields['filters'].fields = fields
