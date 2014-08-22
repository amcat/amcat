##########################################################################
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
from django.forms import ChoiceField
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.aggregate import sort, transpose
from amcat.tools.keywordsearch import SelectionSearch

AXES = tuple((c, c.title()) for c in ("date", "medium", "total", "term"))
INTERVALS = tuple((c, c.title()) for c in ("day", "week", "month", "quarter", "year"))
TRANSPOSE = {"text/json+aggregation+graph"}


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return int(mktime(obj.timetuple())) * 1000
        return super(DatetimeEncoder, self).default(obj)


class AggregationActionForm(QueryActionForm):
    x_axis = ChoiceField(choices=AXES, initial="date")
    y_axis = ChoiceField(choices=AXES, initial="medium")
    interval = ChoiceField(choices=INTERVALS, help_text="Test", required=False, initial="day")


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

        aggregation = selection.get_aggregate(
            form.cleaned_data['x_axis'],
            form.cleaned_data['y_axis'],
            form.cleaned_data['interval']
        )

        if form.cleaned_data["output_type"] in TRANSPOSE:
            aggregation = transpose(aggregation)

        self.monitor.update(60, "Serialising..".format(**locals()))
        return json.dumps(list(sort(aggregation)), cls=DatetimeEncoder, check_circular=False)

