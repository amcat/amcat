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
from __future__ import unicode_literals

from django.views.generic.base import TemplateView
from amcat.tools.amcates import ES

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from amcat.scripts.forms import SelectionForm
from navigator.views.project_views import ProjectDetailsView


class QueryView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, TemplateView):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'query'
    view_name = 'query'
    
    def get_context_data(self, **kwargs):
        articleset_ids = map(int, filter(unicode.isdigit, self.request.GET.get("sets", "").split(",")))
        articlesets = self.project.all_articlesets().filter(id__in=articleset_ids)
        articlesets = articlesets.only("id", "name")

        statistics = ES().statistics(query="*", filters={
            "sets": [aset.id for aset in articlesets]
        })

        form = SelectionForm(
            project=self.project,
            articlesets=articlesets,
            data=self.request.GET,
            initial={
                "datetype": "all",
                "articlesets": articlesets
            }
        )

        form.fields["articlesets"].widget.attrs['disabled'] = 'disabled'
        return dict(super(QueryView, self).get_context_data(), **locals())
