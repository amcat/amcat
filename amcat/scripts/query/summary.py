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

from django.forms import IntegerField, BooleanField
from django.http import QueryDict
from django.template import Context
from django.template.loader import get_template

from amcat.forms.forms import order_fields
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.keywordsearch import SelectionSearch
from amcat.tools.toolkit import Timer


TEMPLATE = get_template('query/summary/summary.html')


@order_fields(("offset", "size"))
class SummaryActionForm(QueryActionForm):
    size = IntegerField(initial=40)
    offset = IntegerField(initial=0)
    aggregations = BooleanField(initial=True, required=False)


class SummaryAction(QueryAction):
    output_types = (("text/html+summary", "HTML"),)
    form_class = SummaryActionForm

    def run(self, form):
        form_data = json.dumps(dict(form.data._iterlists()))

        size = form.cleaned_data['size']
        offset = form.cleaned_data['offset']
        show_aggregation = form.cleaned_data['aggregations']

        with Timer() as timer:
            selection = SelectionSearch(form)
            self.monitor.update(1, "Executing query..")
            narticles = selection.get_count()
            self.monitor.update(39, "Fetching mediums..".format(**locals()))
            mediums = selection.get_mediums()
            self.monitor.update(59, "Fetching articles..".format(**locals()))
            articles = selection.get_articles(size=size, offset=offset)

            if show_aggregation:
                self.monitor.update(69, "Aggregating..".format(**locals()))
                date_aggr = selection.get_aggregate(x_axis="date", y_axis="total", interval="day")
                medium_aggr = selection.get_aggregate(x_axis="medium", y_axis="date", interval="day")

            self.monitor.update(79, "Rendering results..".format(**locals()))

        return TEMPLATE.render(Context(dict(locals(), **{
            "project": self.project, "user": self.user
        })))

