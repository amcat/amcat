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
import json
from datetime import datetime
from time import mktime

from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db.models import Q
from django.forms import ChoiceField, CharField, Select

from amcat.models import Medium, ArticleSet, CodingSchema, CodingSchemaField
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.aggregate import get_relative
from amcat.tools.aggregate_orm import ORMAggregate
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery

from aggregation import AggregationEncoder
from amcat.models.coding.codingschemafield import  FIELDTYPE_IDS

X_AXES = tuple((c, c.title()) for c in ("date", "medium"))
Y_AXES = tuple((c, c.title()) for c in ("medium", "total"))
Y_AXES_2ND = (("", "-------"),) + Y_AXES

INTERVALS = tuple((c, c.title()) for c in ("day", "week", "month", "quarter", "year"))


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
        if src == "Sentence field": continue #TODO: skip sentence fields for now
        category_fields = list(get_category_fields(fields))
        if category_fields: yield src, category_fields

        if values:
            value_fields = list(get_value_fields(fields))
            if value_fields: yield src + " values", value_fields


def get_category_fields(fields):
    for field in fields:
        if field.fieldtype_id in (FIELDTYPE_IDS.CODEBOOK,):
            yield "schemafield_cat_%s" % field.id, field.label
            
def get_value_fields(fields):
    for field in fields:
        if field.fieldtype_id in (FIELDTYPE_IDS.INT, FIELDTYPE_IDS.QUALITY):
            yield "schemafield_avg_%s" % field.id, "Average " +field.label
    

class CodingAggregationActionForm(QueryActionForm):
    x_axis = ChoiceField(label="X-axis (rows)", choices=X_AXES, initial="date")
    y_axis = ChoiceField(label="Y-axis (columns)", choices=Y_AXES, initial="medium")
    interval = ChoiceField(choices=INTERVALS, required=False, initial="day")
    relative_to = CharField(widget=Select, required=False)

    # This field is ignored server-side, but processed by javascript. It causes the renderer
    # to make another call
    y_axis_2 = ChoiceField(label="2nd Y-axis (columns)", choices=Y_AXES, required=False)

    def __init__(self, *args, **kwargs):
        super(CodingAggregationActionForm, self).__init__(*args, **kwargs)

        self.fields["relative_to"].widget.attrs = {
            "class": "depends-will-be-added-by-query-js",
            "data-depends-on": json.dumps(["y_axis", "query", "mediums"]),
            "data-depends-url": "/api/v4/query/statistics/?project={project}&format=json",
            "data-depends-value": "{id}",
            "data-depends-label": "{label}",
        }

        assert self.codingjobs

        
        x_extra = tuple(get_schemafield_choices(self.codingjobs, values=False))
        y_extra = tuple(get_schemafield_choices(self.codingjobs, values=True))
        self.fields["x_axis"].choices = X_AXES + x_extra
        self.fields["y_axis"].choices = Y_AXES + y_extra
        self.fields["y_axis_2"].choices = Y_AXES_2ND + y_extra

    def clean_relative_to(self):
        column = self.cleaned_data['relative_to']

        if not column:
            return None

        y_axis = self.cleaned_data['y_axis']

        if y_axis == "medium":
            if int(column) not in (m.id for m in self.cleaned_data["mediums"]):
                raise ValidationError(MEDIUM_ERR.format(column=column))
            return Medium.objects.get(id=int(column))

        if y_axis == "term":
            queries = SelectionSearch(self).get_queries()
            queries = {q.label: q for q in queries}
            if column not in queries:
                raise ValidationError("Term '{column}' not found in search terms.".format(column=column))
            return queries[column]

        if y_axis == "set":
            if int(column) not in (aset.id for aset in self.articlesets):
                raise ValidationError("Set '{column}' not available.".format(column=column))
            return ArticleSet.objects.get(id=int(column))

        raise ValidationError("Not a valid column name.")


class CodingAggregationAction(QueryAction):
    """
    Aggregate articles based on their properties. Make sure x_axis != y_axis.
    """
    output_types = (
        ("text/json+aggregation+table", "Table"),
        ("text/json+aggregation+barplot", "Bar plot"),
        ("text/json+aggregation+scatter", "Scatter plot"),
        ("text/json+aggregation+line", "Line plot"),
        ("text/json+aggregation+heatmap", "Heatmap"),
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
        x_axis = form.cleaned_data['x_axis']
        y_axis = form.cleaned_data['y_axis']
        interval = form.cleaned_data['interval']

        article_ids = selection.get_article_ids()
        orm_aggregate = ORMAggregate(codingjobs, article_ids)
        aggregation = sorted(orm_aggregate.get_aggregate(x_axis, y_axis, interval))

        self.monitor.update(20, "Calculating relative values..".format(**locals()))
        column = form.cleaned_data['relative_to']

        if column is not None:
            aggregation = list(get_relative(aggregation, column))

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(list(aggregation), cls=AggregationEncoder, check_circular=False)


class AggregationColumnAction(QueryAction):
    pass
