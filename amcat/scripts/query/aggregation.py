# #########################################################################
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
from django.forms import ChoiceField, CharField
from amcat.models import Medium
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.djangotoolkit import parse_date
from amcat.tools.keywordsearch import SelectionSearch, SearchQuery

AXES = tuple((c, c.title()) for c in ("date", "medium", "total", "term"))
INTERVALS = tuple((c, c.title()) for c in ("day", "week", "month", "quarter", "year"))
TRANSPOSE = {"text/json+aggregation+graph"}


class AggregationEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return int(mktime(obj.timetuple())) * 1000
        if isinstance(obj, Medium):
            return {"id": obj.id, "label": obj.name}
        if isinstance(obj, SearchQuery):
            return {"id": obj.label, "label": obj.query}
            pass
        return super(AggregationEncoder, self).default(obj)


MEDIUM_ERR = "Could not find medium with id={column} or name={column}"


def _get_medium(column):
    if column.isdigit():
        try:
            return Medium.objects.get(id=int(column))
        except Medium.DoesNotExist:
            pass

    try:
        return Medium.objects.get(name=column)
    except Medium.DoesNotExist:
        raise ValidationError(MEDIUM_ERR.format(column=column))
    except MultipleObjectsReturned:
        raise ValidationError("Found multiple mediums for name={column}".format(**locals()))


class AggregationActionForm(QueryActionForm):
    x_axis = ChoiceField(label="X-axis (rows)", choices=AXES, initial="date")
    y_axis = ChoiceField(label="Y-axis (columns)", choices=AXES, initial="medium")
    interval = ChoiceField(choices=INTERVALS, required=False, initial="day")
    relative_to = CharField(required=False, help_text=(
        "Enter medium, term or date for which to make the counts "
        "relative to. Accepted: medium id, medium label, DD-MM-YYYY, term. "))

    def clean_relative_to(self):
        column = self.cleaned_data['relative_to']
        y_axis = self.cleaned_data['y_axis']

        if not column:
            return None

        if y_axis == "medium":
            medium = _get_medium(column)
            if medium not in self.cleaned_data["mediums"]:
                raise ValidationError(MEDIUM_ERR.format(column=column))
            return medium.id

        if y_axis == "date":
            try:
                date = parse_date(column)
            except ValueError:
                raise ValidationError("Not a valid date.")

            if date is None:
                raise ValidationError("Not a valid date.")

            # TODO: We should check whether date is within bounds, but it is not certain
            # TODO: those values are in cleaned_data yet. Just error upon rendering..?
            return datetime.combine(date, datetime.min.time())

        if y_axis == "term":
            queries = SelectionSearch(self).get_queries()
            if column not in (q.label for q in queries):
                raise ValidationError("Term '{column}' not found in search terms.".format(column=column))
            return column

        raise ValidationError("Not a valid column name.")


class AggregationAction(QueryAction):
    """
    Aggregate articles based on their properties. Make sure x_axis != y_axis.
    """
    output_types = (
        ("text/json+aggregation+table", "Table"),
        ("text/json+aggregation+graph", "Graph"),
        ("text/json+aggregation+heatmap", "Heatmap"),
        ("text/csv", "CSV (Download)"),
    )
    form_class = AggregationActionForm

    def run(self, form):
        self.monitor.update(1, "Executing query..")
        selection = SelectionSearch(form)
        narticles = selection.get_count()
        self.monitor.update(10, "Found {narticles} articles. Aggregating..".format(**locals()))

        # Get aggregation
        aggregation = selection.get_aggregate(
            form.cleaned_data['x_axis'],
            form.cleaned_data['y_axis'],
            form.cleaned_data['interval']
        )

        #
        self.monitor.update(20, "Calculating relative values..".format(**locals()))
        column = form.cleaned_data['relative_to']

        #if column is not None:
        #    aggregation = list(make_relative(aggregation, column))

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(list(aggregation), cls=AggregationEncoder, check_circular=False)

