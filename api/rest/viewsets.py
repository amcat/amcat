from amcat.models.authorisation import ROLE_PROJECT_READER, ROLE_PROJECT_WRITER, ROLE_PROJECT_ADMIN
from rest_framework import permissions
from django.core.urlresolvers import reverse


_PERM_MAP = {
    'OPTIONS' : None,
    'HEAD' : None,
    'GET' : ROLE_PROJECT_READER,
    'POST' : ROLE_PROJECT_WRITER,
    'DELETE' : ROLE_PROJECT_ADMIN
    }


class ProjectPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user if request.user.is_authenticated() else None
        required_role_id = _PERM_MAP[request.method]
        if not required_role_id: return True
        actual_role_id = view.get_project().get_role_id(user=user)
        if not actual_role_id >= required_role_id:
            log.warn("User {user} has role {actual_role_id} < {required_role_id}".format(**locals()))
        return actual_role_id >= required_role_id
 
class ProjectViewSetMixin(object):
    """
    Mixin for view sets contained in a project.
    Managed permissions
    """
    
    permission_classes = (ProjectPermission,)

    def get_project(self):
        raise NotImplementedError()
        
    def get_url(self, *args, **kwargs):
        return reverse(, args=args, kargs=kargs)

def get_viewsets():
    from api.rest.resources.article import ArticleViewSet
    from api.rest.resources.articleset import ArticleSetViewSet
    return [ArticleViewSet, ArticleSetViewSet]
