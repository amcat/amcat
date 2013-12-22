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

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from api.rest.datatable import Datatable
from api.rest.resources import CodingJobResource
from navigator.views.datatableview import DatatableMixin
from amcat.models import CodingJob
from navigator.utils.misc import session_pop


class CodingJobListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = CodingJob
    parent = None
    base_url = "projects/(?P<project_id>[0-9]+)"
    context_category = 'Coding'
    resource = CodingJobResource

    def get_context_data(self, **kwargs):
        ctx = super(CodingJobListView, self).get_context_data(**kwargs)

        deleted = session_pop(self.request.session, "deleted_codingjob")
        added = session_pop(self.request.session, "added_codingjob")
        if added:
            added = [CodingJob.objects.get(pk=i) for i in added]

        ctx.update(**locals())
        return ctx
