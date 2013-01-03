from amcat.models import User

from api.rest.resources.amcatresource import AmCATResource


class UserResource(AmCATResource):
    model = User
    extra_filters = ["userprofile__affiliation__id"]

    @classmethod
    def get_label(cls):
        return "{username}"
