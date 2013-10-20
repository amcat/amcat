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

from django.views.generic.base import ContextMixin, TemplateResponseMixin, TemplateView
from django.views.generic.edit import CreateView
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory


from api.rest import resources
from api.rest.datatable import Datatable

from amcat.models import authorisation, Project
from django.core.exceptions import PermissionDenied

from settings.menu import PROJECT_MENU

class ProjectViewMixin(object):
    """
    Mixin for all 'project' views (e.g. project details, articlesets) that:
    - Checks whether user has the required access to this project
    - Makes the project available as self.project and as 'project' in the context

    This mixin has two parameters (class variables):
    - projectid_url_kwarg: The name of the url parameter for the project id (default: projectid)
    - required_project_permission: The required permission level on the project for accessing
                                   this view (default: metareader)
    """
    project_id_url_kwarg = 'projectid'
    required_project_permission = authorisation.ROLE_PROJECT_METAREADER

    def get_context_data(self, **kwargs):
        context = super(ProjectViewMixin, self).get_context_data(**kwargs)
        context["project"] = self.project
        context["context"] = self.project # for menu / backwards compat.
        context["menu"] = PROJECT_MENU
        return context
    
    def get_project(self):
        pid = self.kwargs.get(self.project_id_url_kwarg)
        return Project.objects.get(pk=pid)

    def dispatch(self, request, *args, **kwargs):
        self.project = self.get_project()
        self.check_permission()
        return super(ProjectViewMixin, self).dispatch(
            request, *args, **kwargs)

    def check_permission(self):
        if not self.request.user.get_profile().has_role(self.required_project_permission, self.project):
            raise PermissionDenied("User {self.request.user} has insufficient rights on project {self.project}".format(**locals()))
        
    def _get_project(self):
        projectid = Project.objects.get(pk=self.kwargs)
