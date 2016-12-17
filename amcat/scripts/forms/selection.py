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


from itertools import filterfalse
import datetime
import json
import logging
import itertools
import hashlib
from amcat.tools import aggregate_es, aggregate_orm

from django import forms
from django.core.exceptions import ValidationError

from amcat.models import Codebook, Language, Article, ArticleSet, CodingJob, CodingSchemaField, Code, \
    CodebookCode, CodingSchema
from amcat.models.coding.codingschemafield import FIELDTYPE_IDS
from amcat.forms.forms import order_fields
from amcat.tools.caching import cached
from amcat.tools.keywordsearch import SelectionSearch
from amcat.tools.toolkit import to_datetime
from amcat.tools.djangotoolkit import db_supports_distinct_on
from django.db.models import Model
from django.db.models.query import QuerySet

log = logging.getLogger(__name__)

DATETYPES = {
    "all": "All Dates",
    "on": "On",
    "before": "Before",
    "after": "After",
    "between": "Between",
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
    elif isinstance(value, (aggregate_orm.Category, aggregate_orm.Value, aggregate_es.Category)):
        return repr(value)
    elif value is None:
        return value

    raise ValueError("Could not prepare {} of type {} for serialization".format(value, type(value)))


@order_fields()
class SelectionForm(forms.Form):
    include_all = forms.BooleanField(label="Include articles not matched by any keyword", required=False, initial=False)
    articlesets = ModelMultipleChoiceFieldWithIdLabel(queryset=ArticleSet.objects.none(), required=False, initial=())
    codingjobs = ModelMultipleChoiceFieldWithIdLabel(queryset=CodingJob.objects.none(), required=False, initial=())
    article_ids = forms.CharField(widget=forms.Textarea, required=False)
    start_date = forms.DateField(required=False)
    end_date = forms.DateField(required=False)
    datetype = forms.ChoiceField(choices=DATETYPES.items(), initial='all', required=True)
    on_date = forms.DateField(required=False)

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
        self.codingjobs = codingjobs or CodingJob.objects.none()
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

            for field_name in ("1", "2", "3"):
                self.fields["codingschemafield_{}".format(field_name)].queryset = schemafields_codebooks
                self.fields["codingschemafield_value_{}".format(field_name)].queryset = codes
                self.fields["codingschemafield_value_{}".format(field_name)].widget.attrs = {
                    "class": "depends",
                    "data-depends-on": json.dumps(["codingschemafield_{}".format(field_name), "project"]),
                    "data-depends-url": "/api/v4/projects/{project}/codebooks/{codebook}/?format=json",
                    "data-depends-value": "{code}",
                    "data-depends-label": "{code} - {label}",
                }

        if data is not None:
            self.data = self.get_data()


    def get_hash(self, ignore_fields=()) -> str:
        """
        Calculate a hash based on current form. Form *must* be cleaned and valid before executing
        this method. Method returns a SHA256 hexdigest.
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

        if "datetype" not in self.cleaned_data:
            # Don't bother checking, datetype raised ValidationError
            return on_date

        datetype = self.cleaned_data["datetype"]

        if datetype == "on" and not on_date:
            raise ValidationError("'On date' should be defined when dateype is 'on'", code="missing")

        if datetype == "on":
            self.cleaned_data["datetype"] = "between"
            self.cleaned_data["start_date"] = on_date
            self.cleaned_data["end_date"] = on_date + DAY_DELTA

        return None

    def clean_articlesets(self):
        if not self.cleaned_data["articlesets"]:
            return self.project.all_articlesets()
        return self.cleaned_data["articlesets"]

    def clean_article_ids(self):
        article_ids = self.cleaned_data["article_ids"].split("\n")
        article_ids = filter(bool, map(str.strip, article_ids))

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
            raise ValidationError(
                ("Articles {offenders} not in chosen articlesets or some non-existent"
                 .format(**locals())), code="invalid")

        return article_ids

    def clean(self):
        # This is a bit of a hack. We need all the other fields to be correclty validated
        # in order to validate the query field.
        SelectionSearch(self).get_query()
        return self.cleaned_data
        #return super().clean()

