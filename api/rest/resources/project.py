from amcat.models import Project

from api.rest.resources.amcatresource import AmCATResource


class ProjectResource(AmCATResource):
    model = Project
    extra_filters = ['projectrole__user__id']
