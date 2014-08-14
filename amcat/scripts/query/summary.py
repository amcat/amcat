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
from django.forms import IntegerField
from django.template import Context
from django.template.loader import get_template
from amcat.forms.forms import order_fields
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.keywordsearch import SelectionSearch

TEMPLATE = get_template('query/summary.html')


@order_fields(("offset", "size"))
class SummaryActionForm(QueryActionForm):
    size = IntegerField(initial=20)
    offset = IntegerField(initial=0)


class SummaryAction(QueryAction):
    """
    This is the docstring of SummaryAction!
    """
    output_types = (("text/html", "Inline"),)
    form_class = SummaryActionForm

    def run(self, form):
        size = form.cleaned_data['size']
        offset = form.cleaned_data['offset']

        selection = SelectionSearch(form)
        self.monitor.update(1, "Creating summary")
        narticles = selection.get_count()
        self.monitor.update(39, "Found {narticles} articles in total".format(**locals()))
        articles = selection.get_articles(size=size, offset=offset)
        self.monitor.update(79, "Rendering results..".format(**locals()))

        return TEMPLATE.render(Context(dict(locals(), **{
            "project": self.project, "user": self.user
        })))

