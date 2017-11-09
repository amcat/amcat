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

from amcat.models.project import Project, LAST_VISITED_FIELD_NAME
from django.db.models import Q
from django.db.models.expressions import RawSQL
from api.rest.resources.amcatresource import AmCATResource
from api.rest.viewsets.project import ProjectSerializer

class ProjectResource(AmCATResource):
    model = Project
    extra_filters = ['projectrole__user__id']
    ordering_fields = ("id", "name", "description", "insert_date", "active", LAST_VISITED_FIELD_NAME)
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()

    def filter_queryset(self, queryset):
        qs = super(ProjectResource, self).filter_queryset(queryset)

        # only show projects that are either public or the user has a role in
        if self.request.user.is_anonymous():
            qs = qs.filter(guest_role__isnull=False)
        elif not self.request.user.is_superuser: 
            qs = qs.filter(Q(guest_role__isnull=False) | Q(projectrole__user_id=self.request.user.id)).distinct()


        qs = self._filter_order_null_last(qs)
        return qs

    def _filter_order_null_last(self, qs):
        orderby = self.request.query_params.get('order_by', [])
        if isinstance(orderby, str):
            orderby = [orderby]
        try:
            idx = orderby.index(LAST_VISITED_FIELD_NAME
                                if LAST_VISITED_FIELD_NAME in orderby
                                else ("-" + LAST_VISITED_FIELD_NAME))
        except ValueError:
            #Not ordered by last visited
            pass
        else:
            qs = qs.annotate(visited=
                RawSQL("select projects.project_id in (select urp.project_id from user_recent_projects as urp where user_id = %s)",
                    (self.request.user.userprofile.id,)))
            orderby.insert(idx, '-visited')
            qs = qs.order_by(*orderby)
        return qs
