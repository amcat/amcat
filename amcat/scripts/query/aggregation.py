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
from csv import DictWriter
from cStringIO import StringIO

from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.db.models import Q
from django.forms import ChoiceField, CharField, Select, BooleanField

from api.rest.tablerenderer import CSVRenderer
from amcat.models import Medium, ArticleSet, CodingSchema, CodingSchemaField
from amcat.scripts.query import QueryAction, QueryActionForm, QueryActionHandler
from amcat.tools.aggregate import get_relative, fill_zeroes
from amcat.tools.aggregate_orm import ORMAggregate
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery

X_AXES = tuple((c, c.title()) for c in ("date", "medium", "term", "set"))
Y_AXES = tuple((c, c.title()) for c in ("medium", "term", "set", "total"))

X_AXES_CODINGJOB = tuple((c, c.title()) for c in ("date", "medium"))
Y_AXES_CODINGJOB = tuple((c, c.title()) for c in ("medium", "total"))
Y_AXES_CODINGJOB_2ND = (("", "-------"),) + Y_AXES_CODINGJOB

INTERVALS = tuple((c, c.title()) for c in ("day", "week", "month", "quarter", "year"))


class AggregationEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Medium) or isinstance(obj, ArticleSet):
            return {"id": obj.id, "label": obj.name}
        if isinstance(obj, SearchQuery):
            return {"id": obj.label, "label": obj.query}
        if isinstance(obj, CodingSchemaField):
            return {"id": obj.id, "label": obj.label}
        return super(AggregationEncoder, self).default(obj)


MEDIUM_ERR = "Could not find medium with id={column} or name={column}"

def get_all_schemafields(codingjobs):
    codingjob_ids = [c.id for c in codingjobs]
    unitschema_filter = Q(codingjobs_unit__id__in=codingjob_ids)
    articleschema_filter = Q(codingjobs_article__id__in=codingjob_ids)
    codingschemas = CodingSchema.objects.filter(unitschema_filter | articleschema_filter)
    schemafields = CodingSchemaField.objects.filter(codingschema__in=codingschemas)
    return schemafields

def get_schemafield_choices(codingjobs):
    schemafields = get_all_schemafields(codingjobs).order_by("label").only("id", "label")
    article_fields = schemafields.filter(codingschema__isarticleschema=True)
    sentence_fields = schemafields.filter(codingschema__isarticleschema=False)

    yield ("Article field", [("schemafield_avg_%s" % s.id, "Average: " +s.label) for s in article_fields])
    yield ("Sentence field", [("schemafield_avg_%s" % s.id, "Average: " + s.label) for s in sentence_fields])


class AggregationActionForm(QueryActionForm):
    x_axis = ChoiceField(label="X-axis (rows)", choices=X_AXES, initial="date")
    y_axis = ChoiceField(label="Y-axis (columns)", choices=Y_AXES, initial="medium")
    interval = ChoiceField(choices=INTERVALS, required=False, initial="day")
    relative_to = CharField(widget=Select, required=False)

    # This field is ignored server-side, but processed by javascript. It causes the renderer
    # to make another call
    y_axis_2 = ChoiceField(label="2nd Y-axis (columns)", choices=Y_AXES, required=False)

    list_zeroes = BooleanField(label="List empty dates as 0.", initial=True,  required=False)

    def __init__(self, *args, **kwargs):
        super(AggregationActionForm, self).__init__(*args, **kwargs)

        self.fields["relative_to"].widget.attrs = {
            "class": "depends-will-be-added-by-query-js",
            "data-depends-on": json.dumps(["y_axis", "query", "mediums"]),
            "data-depends-url": "/api/v4/query/statistics/?project={project}&format=json",
            "data-depends-value": "{id}",
            "data-depends-label": "{label}",
        }

        if self.codingjobs:
            schemafield_choices = tuple(get_schemafield_choices(self.codingjobs))
            self.fields["x_axis"].choices = X_AXES_CODINGJOB
            self.fields["y_axis"].choices = Y_AXES_CODINGJOB + schemafield_choices
            self.fields["y_axis_2"].choices = Y_AXES_CODINGJOB_2ND + schemafield_choices
        else:
            del self.fields["y_axis_2"]

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

class AggregationHandler(QueryActionHandler):

    def get_response(self):
        response = super(AggregationHandler, self).get_response()
        form = self.get_query_action().get_form()
        if form.cleaned_data["output_type"] == "text/csv":
            response["Content-Disposition"] = 'attachment; filename="aggregation.csv"'
        return response

class AggregationAction(QueryAction):
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
    form_class = AggregationActionForm
    task_handler = AggregationHandler

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

        # Ugly hack to see if we need postgres aggregation (because of codingjobs analyses),
        # or whether we can just pass it to elastic
        if y_axis.startswith("schemafield_avg_"):
            article_ids = selection.get_article_ids()
            orm_aggregate = ORMAggregate(codingjobs, article_ids)
            aggregation = sorted(orm_aggregate.get_aggregate(x_axis, y_axis, interval))
        else:
            aggregation = selection.get_aggregate(x_axis, y_axis, interval)

        if x_axis == "date" and 'list_zeroes' in form.cleaned_data and form.cleaned_data['list_zeroes']:
            aggregation = fill_zeroes(aggregation, interval)

        self.monitor.update(20, "Calculating relative values..".format(**locals()))
        column = form.cleaned_data['relative_to']

        if column is not None:
            aggregation = list(get_relative(aggregation, column))

        self.monitor.update(60, "Serialising..".format(**locals()))
        if form.cleaned_data["output_type"] == "text/csv":
            serializer = AggregationCSVSerializer()
            return serializer.csv_serialize(aggregation, x_axis, y_axis)
        return json.dumps(list(aggregation), cls=AggregationEncoder, check_circular=False)


class AggregationCSVSerializer:
    def csv_serialize(self, aggregation, x_axis, y_axis):
        srio = StringIO()

        if y_axis == "total":
            self._csv_serialize_totals(aggregation, srio, x_axis)
        else:
            self._csv_serialize_default(aggregation, srio, x_axis)

        result = srio.getvalue()
        srio.close()
        return result


    def _csv_serialize_default(self, aggregation, srio, x_axis):
        fields = set()
        for row in aggregation:
            for col in row[1]:
                field_name = self._csv_field_to_str(col[0])
                if field_name not in fields:
                    fields.add(field_name)
        fields = [x_axis] + list(fields)
        writer = DictWriter(srio, fieldnames=fields, restval=0)
        writer.writeheader()
        for row in aggregation:
            row_dict = {x_axis: self._csv_field_to_str(row[0])}
            for col in row[1]:
                col_name = self._csv_field_to_str(col[0])
                col_value = col[1]
                row_dict[col_name] = col_value
            writer.writerow(row_dict)

    def _csv_serialize_totals(self, aggregation, srio, x_axis):
        fields = [x_axis, "total"]
        writer = DictWriter(srio, fieldnames=fields, restval=0)
        writer.writeheader()
        for row in aggregation:
            row_dict = {"total": row[1], x_axis: self._csv_field_to_str(row[0])}
            writer.writerow(row_dict)

    def _csv_field_to_str(self, field):
        if isinstance(field, Medium) or isinstance(field, ArticleSet):
            return "{} - {}".format(field.id, field.name.encode("utf-8"))

        if isinstance(field, SearchQuery):
            return "{}#{}".format(field.label, field.query)
        return field

class AggregationColumnAction(QueryAction):
    pass
