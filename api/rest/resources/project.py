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

from amcat.models import Project
from django.db.models import Q

from api.rest.resources.amcatresource import AmCATResource
from api.rest.viewsets.project import ProjectSerializer

class ProjectResource(AmCATResource):
    model = Project
    extra_filters = ['projectrole__user__id']
    ordering_fields = ("id", "name", "description", "insert_date", "active")
    serializer_class = ProjectSerializer

    def filter_queryset(self, queryset):
        qs = super(ProjectResource, self).filter_queryset(queryset)
        # only show projects that are either public or the user has a role in
        if self.request.user.is_anonymous():
            qs = qs.filter(guest_role__isnull=False)
        elif not self.request.user.is_superuser: 
            qs = qs.filter(Q(guest_role__isnull=False) | Q(projectrole__user_id=self.request.user.id)).distinct()
        return qs
