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

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from django.views.generic.base import TemplateView
from api.webscripts import mainScripts
from django.db.models import Q

from amcat.models import CodingJob
from amcat.scripts.forms import SelectionForm
from navigator.views.project_views import ProjectDetailsView

class QueryView(ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, TemplateView):
    context_category = 'Query'
    parent = ProjectDetailsView
    url_fragment = 'query'
    view_name = 'query'
    
    def get_context_data(self, **kwargs):
        context = super(QueryView, self).get_context_data(**kwargs)
        p = self.project
        outputs = [dict(id = ws.__name__,
                                   name = ws.name,
                                   formAsHtml= ws.formHtml(project=p))
                              for ws in mainScripts]
        
        all_articlesets = p.all_articlesets()

        favs = tuple(p.favourite_articlesets.filter(Q(project=p.id) | Q(projects_set=p.id))
                     .values_list("id", flat=True))
        
        no_favourites = not favs
        favourites = json.dumps(favs)
    
        codingjobs = json.dumps(tuple(CodingJob.objects.filter(articleset__in=all_articlesets).values_list("articleset_id", flat=True)))
        all_sets = json.dumps(tuple(all_articlesets.values_list("id", flat=True)))

        form = SelectionForm(project=p, data=self.request.GET, initial={"datetype" : "all" })
        context.update(locals())
        return context
