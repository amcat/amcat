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
import re
import json

from datetime import datetime
from time import mktime

from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db.models import Q
from django.forms import ChoiceField, CharField, Select

from amcat.models import Medium, ArticleSet, CodingSchema, CodingSchemaField
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools import aggregate_orm
from amcat.tools.aggregate import get_relative
from amcat.tools.aggregate_orm import ORMAggregate
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery

from aggregation import AggregationEncoder
from amcat.models.coding.codingschemafield import  FIELDTYPE_IDS

AGGREGATION_FIELDS = (
    ("medium", "Medium"),
    ("Interval", (
        ("year", "Year"),
        ("quarter", "Quarter"),
        ("month", "Month"),
        ("week", "Week"),
        ("day", "Day")
    ))
)

AGGREGATION_ORM_MAPPING = {
    "medium": aggregate_orm.MediumCategory,
    "year": aggregate_orm.YearCategory,
    "quarter": aggregate_orm.QuarterCategory,
    "month": aggregate_orm.MonthCategory,
    "week": aggregate_orm.WeekCategory,
    "day": aggregate_orm.DayCategory
}

CODINGSCHEMAFIELD_RE = re.compile("^codingschemafield\((?P<id>[0-9]+)\)$")
AVERAGE_CODINGSCHEMAFIELD_RE = re.compile("^avg\((?P<id>[0-9]+)\)$")

MEDIUM_ERR = "Could not find medium with id={column} or name={column}"

def get_all_schemafields(codingjobs):
    codingjob_ids = [c.id for c in codingjobs]
    unitschema_filter = Q(codingjobs_unit__id__in=codingjob_ids)
    articleschema_filter = Q(codingjobs_article__id__in=codingjob_ids)
    codingschemas = CodingSchema.objects.filter(unitschema_filter | articleschema_filter)
    schemafields = CodingSchemaField.objects.filter(codingschema__in=codingschemas)
    return schemafields

def get_schemafield_choices(codingjobs, values=True):
    schemafields = get_all_schemafields(codingjobs).order_by("label").only("id", "label")
    article_fields = schemafields.filter(codingschema__isarticleschema=True)
    sentence_fields = schemafields.filter(codingschema__isarticleschema=False)

    for src, fields in [("Article field", article_fields), ("Sentence field", sentence_fields)]:
        if src == "Sentence field":
            continue #TODO: skip sentence fields for now

        category_fields = list(get_category_fields(fields))
        if category_fields:
            yield src, category_fields

def get_category_fields(fields):
    for field in fields:
        if field.fieldtype_id in (FIELDTYPE_IDS.CODEBOOK,):
            yield "codingschemafield(%s)" % field.id, field.label
            
def get_value_fields(fields):
    for field in fields:
        if field.fieldtype_id in (FIELDTYPE_IDS.INT, FIELDTYPE_IDS.QUALITY):
            yield "avg(%s)" % field.id, "Average %s" % field.label
    yield "count", "Article count"


class CodingAggregationActionForm(QueryActionForm):
    primary = ChoiceField(label="Primary aggregation", choices=AGGREGATION_FIELDS)
    secondary = ChoiceField(label="Secondary aggregation", choices=(("", "------"),) + AGGREGATION_FIELDS, required=False)

    value1 = ChoiceField(label="First value", initial="count")
    value2 = ChoiceField(label="Second value", required=False, initial="")

    #relative_to = CharField(widget=Select, required=False)

    def __init__(self, *args, **kwargs):
        super(CodingAggregationActionForm, self).__init__(*args, **kwargs)

        assert self.codingjobs

        schemafields = get_all_schemafields(self.codingjobs)

        value_choices = tuple(get_value_fields(schemafields))
        self.fields["value1"].choices = value_choices
        self.fields["value2"].choices = (("", "------"),) + value_choices

        schema_choices = tuple(get_schemafield_choices(self.codingjobs))
        self.fields["primary"].choices += schema_choices
        self.fields["secondary"].choices += schema_choices

    def _clean_aggregation(self, field_name):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        # Test for medium or interval
        category = AGGREGATION_ORM_MAPPING.get(field_value)
        if category:
            return category()

        # Test for schemafield
        match = CODINGSCHEMAFIELD_RE.match(field_value)
        if match:
            codingschemafield_id = int(match.groupdict()["id"])
            codingschemafield = CodingSchemaField.objects.get(id=codingschemafield_id)
            return aggregate_orm.SchemafieldCategory(codingschemafield)

        raise ValidationError("Not a valid aggregation: %s." % field_value)

    def clean_primary(self):
        return self._clean_aggregation("primary")

    def clean_secondary(self):
        return self._clean_aggregation("secondary")

    def _clean_value(self, field_name):
        field_value = self.cleaned_data[field_name]

        if not field_value:
            return None

        if field_value == "count":
            return aggregate_orm.Count()

        match = AVERAGE_CODINGSCHEMAFIELD_RE.match(field_value)
        if match:
            codingschemafield_id = int(match.groupdict()["id"])
            codingschemafield = CodingSchemaField.objects.get(id=codingschemafield_id)
            return aggregate_orm.Average(codingschemafield)

        raise ValidationError("Not a valid value: %s." % field_value)

    def clean_value1(self):
        return self._clean_value("value1")

    def clean_value2(self):
        return self._clean_value("value2")

    def clean(self):
        primary = self.cleaned_data["primary"]
        secondary = self.cleaned_data["secondary"]
        value2 = self.cleaned_data["value2"]

        if primary and secondary and value2:
            error_msg =  "When selecting two aggregations (primary and secondary), "
            error_msg += "you can only select one value."
            raise ValidationError(error_msg)

        return self.cleaned_data


class CodingAggregationAction(QueryAction):
    """
    Aggregate articles based on their properties. Make sure x_axis != y_axis.
    """
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
        orm_aggregate = ORMAggregate(codingjobs, article_ids, flat=True, empty=True)
        categories = list(filter(None, [primary, secondary]))
        values = list(filter(None, [value1, value2]))
        aggregation = sorted(orm_aggregate.get_aggregate(categories, values))

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(list(aggregation), cls=AggregationEncoder, check_circular=False)


class AggregationColumnAction(QueryAction):
    pass
