###########################################################################
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
from itertools import chain
import re
import json

from django.core.exceptions import ValidationError
from django.forms import ChoiceField, BooleanField

from amcat.models import Medium, ArticleSet, CodingJob
from amcat.models import CodingSchemaField, Code, CodingValue, Coding
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools import aggregate_orm
from amcat.tools.aggregate_orm import ORMAggregate
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery
from amcat.scripts.forms.selection import get_all_schemafields
from aggregation import AggregationEncoder
from amcat.models.coding.codingschemafield import  FIELDTYPE_IDS

AGGREGATION_FIELDS = (
    ("articleset", "Articleset"),
    ("medium", "Medium"),
    ("term", "Term"),
    ("Interval", (
        ("year", "Year"),
        ("quarter", "Quarter"),
        ("month", "Month"),
        ("week", "Week"),
        ("day", "Day")
    ))
)

INTERAVLS = ("year", "quarter", "month", "week", "day")

CODINGSCHEMAFIELD_RE = re.compile("^codingschemafield\((?P<id>[0-9]+)\)$")
AVERAGE_CODINGSCHEMAFIELD_RE = re.compile("^avg\((?P<id>[0-9]+)\)$")

MEDIUM_ERR = "Could not find medium with id={column} or name={column}"


def get_schemafield_choices(codingjobs, values=True):
    schemafields = get_all_schemafields(codingjobs).order_by("label").only("id", "label")
    article_fields = schemafields.filter(codingschema__isarticleschema=True)
    sentence_fields = schemafields.filter(codingschema__isarticleschema=False)

    for src, fields in [("Article field", article_fields), ("Sentence field", sentence_fields)]:
        category_fields = list(get_category_fields(fields))
        if category_fields:
            yield src, category_fields

def get_category_fields(fields):
    for field in fields:
        if field.fieldtype_id  == FIELDTYPE_IDS.CODEBOOK:
            yield "codingschemafield(%s)" % field.id, field.label

def get_average_fields(fields):
    for field in fields:
        if field.fieldtype_id in (FIELDTYPE_IDS.INT, FIELDTYPE_IDS.QUALITY):
            yield "avg(%s)" % field.id, "Average %s" % field.label

def get_value_fields(fields):
    yield "Average", list(get_average_fields(fields))
    yield "Count", [
        ("count(articles)", "Number of articles"),
        ("count(codings)", "Number of codings"),
        ("count(codingvalues)", "Number of coding values")
    ]


class CodingAggregationActionForm(QueryActionForm):
    primary_use_codebook = BooleanField(initial=False, required=False)
    primary = ChoiceField(label="Primary aggregation", choices=AGGREGATION_FIELDS)
    secondary_use_codebook = BooleanField(initial=False, required=False)
    secondary = ChoiceField(label="Secondary aggregation", choices=(("", "------"),) + AGGREGATION_FIELDS, required=False)

    value1 = ChoiceField(label="First value", initial="count(articles)")
    value2 = ChoiceField(label="Second value", required=False, initial="")

    #relative_to = CharField(widget=Select, required=False)

    def __init__(self, *args, **kwargs):
        super(CodingAggregationActionForm, self).__init__(*args, **kwargs)

        assert self.codingjobs
        assert self.schemafields is not None

        value_choices = tuple(get_value_fields(self.schemafields))
        self.fields["value1"].choices = value_choices
        self.fields["value2"].choices = (("", "------"),) + value_choices

        schema_choices = tuple(get_schemafield_choices(self.codingjobs))
        self.fields["primary"].choices += schema_choices
        self.fields["secondary"].choices += schema_choices

    def _clean_aggregation(self, field_name, prefix=None):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        if field_value in INTERAVLS:
            return aggregate_orm.IntervalCategory(field_value, prefix=prefix)

        if field_value == "medium":
            return aggregate_orm.MediumCategory(prefix=prefix)

        if field_value == "articleset":
            return aggregate_orm.ArticleSetCategory(prefix=prefix)

        if field_value == "term":
            return aggregate_orm.TermCategory()

        # Test for schemafield
        match = CODINGSCHEMAFIELD_RE.match(field_value)
        if match:
            codingschemafield_id = int(match.groupdict()["id"])
            codingschemafield = CodingSchemaField.objects.get(id=codingschemafield_id)
            use_codebook = self.cleaned_data["{}_use_codebook".format(field_name)]
            codebook = codingschemafield.codebook if use_codebook else None
            return aggregate_orm.SchemafieldCategory(codingschemafield, codebook=codebook, prefix=prefix)

        raise ValidationError("Not a valid aggregation: %s." % field_value)

    def clean_primary(self):
        return self._clean_aggregation("primary", prefix="1")

    def clean_secondary(self):
        return self._clean_aggregation("secondary", prefix="3")

    def _clean_value(self, field_name, prefix=None):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        if field_value == "count(articles)":
            return aggregate_orm.CountArticlesValue(prefix=prefix)

        if field_value == "count(codings)":
            return aggregate_orm.CountCodingsValue(prefix=prefix)

        if field_value == "count(codingvalues)":
            return aggregate_orm.CountCodingValuesValue(prefix=prefix)

        match = AVERAGE_CODINGSCHEMAFIELD_RE.match(field_value)
        if match:
            codingschemafield_id = int(match.groupdict()["id"])
            codingschemafield = CodingSchemaField.objects.get(id=codingschemafield_id)
            return aggregate_orm.AverageValue(codingschemafield, prefix=prefix)

        raise ValidationError("Not a valid value: %s." % field_value)

    def clean_value1(self):
        return self._clean_value("value1", prefix="2")

    def clean_value2(self):
        return self._clean_value("value2", prefix="4")

    def clean(self):
        primary = self.cleaned_data["primary"]
        secondary = self.cleaned_data["secondary"]
        value2 = self.cleaned_data["value2"]

        if primary and secondary and value2:
            error_msg =  "When selecting two aggregations (primary and secondary), "
            error_msg += "you can only select one value."
            raise ValidationError(error_msg)

        return self.cleaned_data

def to_sortable_tuple(key):
    if isinstance(key, tuple):
        return tuple(map(to_sortable_tuple, key))
    elif isinstance(key, (Medium, ArticleSet, CodingJob)):
        return key.name.lower()
    elif isinstance(key, (Code, SearchQuery)):
        return key.label.lower()
    return key


def get_code_filter(codebook, code_id, include_descendants):
    yield code_id

    if include_descendants:
        codebook.cache()
        flat_tree = chain.from_iterable(t.get_descendants() for t in codebook.get_tree())
        flat_tree = chain(flat_tree, codebook.get_tree())
        tree_item = [t for t in flat_tree if t.code_id == code_id][0]
        for descendant in tree_item.get_descendants():
            yield descendant.code_id


class CodingAggregationAction(QueryAction):
    output_types = (
        ("text/json+aggregation+codings+barplot", "Bar plot"),
        ("text/json+aggregation+codingbs+table", "Table"),
        ("text/json+aggregation+codings+scatter", "Scatter plot"),
        ("text/json+aggregation+codings+line", "Line plot"),
        ("text/json+aggregation+codings+heatmap", "Heatmap"),
        ("text/csv", "CSV (Download)"),
    )
    form_class = CodingAggregationActionForm

    def run(self, form):
        self.monitor.update(1, "Executing query..")
        selection = SelectionSearch(form)
        narticles = selection.get_count()
        self.monitor.update(10, "Found {narticles} articles. Aggregating..".format(**locals()))

        # Get aggregation
        codingjobs = form.cleaned_data["codingjobs"]
        primary = form.cleaned_data['primary']
        secondary = form.cleaned_data['secondary']
        value1 = form.cleaned_data['value1']
        value2 = form.cleaned_data['value2']

        article_ids = selection.get_article_ids()

        # This should probably happen in SelectionForm?
        codings = Coding.objects.all()
        codings = codings.filter(coded_article__article__id__in=article_ids)
        codings = codings.filter(coded_article__codingjob__in=codingjobs)

        # To prevent huge 'recursive' queries, we will build our own list of valid
        # coding values ids in Python :)
        coding_ids = set(CodingValue.objects.filter(coding__in=codings).values_list("coding_id", flat=True))
        for field_name in ("1", "2", "3"):
            if not coding_ids:
                break

            schemafield = form.cleaned_data["codingschemafield_{}".format(field_name)]
            schemafield_value = form.cleaned_data["codingschemafield_value_{}".format(field_name)]
            schemafield_include_descendants = form.cleaned_data["codingschemafield_include_descendants_{}".format(field_name)]

            if schemafield and  schemafield_value:
                code_ids = list(get_code_filter(schemafield.codebook, schemafield_value.id, schemafield_include_descendants))
                coding_values = CodingValue.objects.filter(coding__id__in=coding_ids)
                coding_values = coding_values.filter(field__id=schemafield.id)
                coding_values = coding_values.filter(intval__in=code_ids)
                coding_ids.intersection_update(set(coding_values.values_list("coding_id", flat=True)))

        codings = Coding.objects.filter(id__in=coding_ids)

        terms = selection.get_article_ids_per_query()
        orm_aggregate = ORMAggregate(codings, flat=False, terms=terms)
        categories = list(filter(None, [primary, secondary]))
        values = list(filter(None, [value1, value2]))
        aggregation = orm_aggregate.get_aggregate(categories, values)
        aggregation = sorted(aggregation, key=to_sortable_tuple)

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(list(aggregation), cls=AggregationEncoder, check_circular=False)


class AggregationColumnAction(QueryAction):
    pass
