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

import re
from typing import Union

from django.contrib import messages
from django.forms import Form
from django.http import Http404, HttpResponseNotAllowed
from django.views.generic.base import RedirectView, View
from django.views.generic.edit import FormView, UpdateView
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied

import settings
from amcat.models import authorisation, Project, ArticleSet, PROJECT_ROLES
from amcat.models.project import RecentProject
from navigator.views.scriptview import ScriptView

from amcat.tools.usage import log_request_usage


class BreadCrumbMixin(object):

    def get_context_data(self, **kwargs):
        context = super(BreadCrumbMixin, self).get_context_data(**kwargs)
        context["breadcrumbs"] = list(self.get_breadcrumbs())
        return context

    def get_breadcrumbs(self):
        bc = self._get_breadcrumbs(self.kwargs, self)
        return bc

    def _get_breadcrumbs(cls, kwargs, view):
        return []

class ProjectPermissionMap:
    _methods = ("GET", "POST", "PUT", "DELETE")
    def __init__(self,
                 all: PROJECT_ROLES = None,
                 get: PROJECT_ROLES = None,
                 post: PROJECT_ROLES = None,
                 put: PROJECT_ROLES = None,
                 delete: PROJECT_ROLES = None):
        self.get = get if get is not None else all
        self.post = post if post is not None else all
        self.put = put if put is not None else all
        self.delete = delete if delete is not None else all

    def role_id(self, method: str) -> int:
        return getattr(self, method.lower()).value

class ProjectViewMixin(View):

    """
    Mixin for all 'project' views (e.g. project details, articlesets) that:
    - Checks whether user has the required access to this project
    - Makes the project available as self.project and in the template context

    This mixin has two parameters (class variables):
    - projectid_url_kwarg: The name of the url parameter for the project id
                           (default: projectid)
    - required_project_permission: The required permission level on the project
                                   for accessing this view
                                   (default: metareader)
    """
    project_id_url_kwarg = 'project'
    articleset_id_url_kwarg = 'articleset'
    required_project_permission = PROJECT_ROLES.METAREADER
    help_context = None

    @property
    def project(self):
        if not hasattr(self, "_project"):
            self._project = self.get_project()
        return self._project

    @property
    def articleset(self):
        if not hasattr(self, "_articleset"):
            self._articleset = self.get_articleset()
            if self._articleset is None:
                raise AttributeError("Property 'articleset' is invalid in this view")
        return self._articleset

    def get_context_data(self, **kwargs):
        context = super(ProjectViewMixin, self).get_context_data(**kwargs)

        #most of this is redundant, 'self' exists in context as 'view'.
        context["project"] = self.project
        context["context"] = self.project  # for menu / backwards compat.
        context["can_edit"] = self.can_edit()
        context["is_admin"] = self.is_admin()
        context["can_view_text"] = self.can_view_text()
        context["main_active"] = 'Projects'
        context["help_context"] = self.get_help_context()
        context["context_category"] = self.get_context_category()
        context["notification"] = (self.request.session
                                   .pop("notification", None))
        return context

    @classmethod
    def get_context_category(cls):
        return getattr(cls, "context_category", None)

    def get_project(self):
        pid = self.kwargs.get(self.project_id_url_kwarg)
        try:
            return Project.objects.get(pk=pid)
        except Project.DoesNotExist:
            raise Http404("Project not found")

    def get_articleset(self):
        if self.articleset_id_url_kwarg not in self.kwargs:
            # kwarg is not given, this view has no articleset.
            return None

        aset_id = self.kwargs[self.articleset_id_url_kwarg]
        try:
            return ArticleSet.objects.get(pk=aset_id)
        except ArticleSet.DoesNotExist:
            raise Http404("Articleset not found")

    def dispatch(self, request, *args, **kwargs):
        # HACK: remove query from session to prevent 'permanent' highlighting
        self.last_query = self.request.session.pop("query", None)

        if not self.request.user.is_anonymous():
            RecentProject.update_visited(self.request.user.userprofile, self.project)

        self.check_permission(request.method)
        return super(ProjectViewMixin, self).dispatch(request, *args, **kwargs)

    @classmethod
    def get_required_project_permissions(cls) -> Union[int, PROJECT_ROLES, ProjectPermissionMap]:
        """
        Returns the required project permissions. Either a single int or PROJECT_ROLES object giving
        one permission for all methods, or a ProjectPermissionMap.
        """
        return cls.get_required_project_permissions()

    def has_permission(self, perm):
        return self.project.has_role(self.request.user, perm)

    def check_permission(self, method: str = "GET"):
        permission = self.required_project_permission
        if isinstance(permission, ProjectPermissionMap):
            permission = permission.role_id(method)
        else:
            permission = getattr(permission, "value", permission)

        if not self.has_permission(permission):
            raise PermissionDenied("User {self.request.user} has insufficient "
                                   "rights on project {self.project}"
                                   .format(**locals()))

    def can_view_text(self):
        """Checks if the user has the right to edit this project"""
        return self.has_permission(authorisation.ROLE_PROJECT_READER)

    def can_edit(self):
        """Checks if the user has the right to edit this project"""
        return self.has_permission(authorisation.ROLE_PROJECT_WRITER)

    def is_admin(self):
        """Checks if the user has the right to edit this project"""
        return self.has_permission(authorisation.ROLE_PROJECT_ADMIN)

    def get_breadcrumbs(self):
        bc = self._get_breadcrumbs(self.kwargs, self)
        bc.insert(0, ("Projects", reverse("navigator:projects")))
        return bc

    def get_template_names(self):

        if self.template_name is not None:
            return [self.template_name]
        else:
            name = re.sub("[- ]", "_", self.get_view_name())
            return ["project/{name}.html".format(**locals())]

    def get_help_context(self):
        
        if self.help_context is not None:
            return self.help_context
        return re.sub("[-_]", " ", self.get_view_name()).title()


from django.views.generic.list import ListView


class HierarchicalViewMixin(object):

    def get_context_data(self, **kwargs):
        context = super(HierarchicalViewMixin, self).get_context_data(**kwargs)
        try:
            project = self.get_project()
        except:
            project = None
        try:
            obj = self.get_object()
            obj = "{} {}: {}".format(obj.__class__.__name__, obj.id, str(obj))
        except:
            obj = None
            
        log_request_usage(self.request, "view", self.get_view_name(), project, object=obj)
        context["object"] = self.get_object
        return context

    def get_object(self):
        return self._get_object(self.kwargs)

    @property
    def pk_url_kwarg(self):
        return self.get_model_key()

    @classmethod
    def get_model(cls):
        """
        Get the model for this class. If no model, check the parent.
        (also check for model=None because SingleObjectMixin sets model=None)
        """
        model = getattr(cls, "model", None)
        return model if model is not None else cls.parent.get_model()

    @classmethod
    def get_context_category(cls):
        return (cls.context_category if hasattr(cls, "context_category")
                else cls.parent.get_context_category())

    @classmethod
    def get_model_key(cls):
        # Accessing db_column may result in None, as it only appears when explicitly
        # set on model definition.
        _, db_column = cls.get_model()._meta.get_field("id").get_attname_column()

        if db_column is None:
            return None

        if db_column.endswith("_id"):
            return db_column[:-3]

        return db_column

    @classmethod
    def get_model_name(cls):
        return cls.get_model()._meta.verbose_name_plural.title()

    @classmethod
    def get_table_name(cls):
        return cls.get_model()._meta.db_table

    @classmethod
    def _get_object(cls, kwargs):
        pk = kwargs[cls.get_model_key()]
        return cls.get_model().objects.get(pk=pk)

    @classmethod
    def _get_view_name(cls):
        name = cls.get_model()._meta.object_name.lower()

        if hasattr(cls, 'url_fragment'):
            name += "-" + cls.url_fragment
        else:
            name += ("-list" if issubclass(cls, ListView) else "-details")

        return name

    @classmethod
    def get_view_name(cls):
        return getattr(cls, "view_name", cls._get_view_name())

    @classmethod
    def get_url_patterns(cls):
        comps = cls._get_url_components()
        return ["^" + "/".join(comps) + "/$"]

    @classmethod
    def get_url_component(cls):
        """Return the url component for this level of the breadcrum trail"""
        if hasattr(cls, 'url_fragment'):
            return cls.url_fragment
        elif issubclass(cls, ListView):
            return cls.get_table_name().lower()
        else:
            return "(?P<{key}>[0-9]+)".format(key=cls.get_model_key())

    @classmethod
    def _get_url_components(cls):
        """Return the url pattern for this view class without suffix"""
        if cls.parent:
            for comp in cls.parent._get_url_components():
                yield comp
        else:
            base = getattr(cls, "base_url", None)
            if base:
                yield base
        yield cls.get_url_component()

    @classmethod
    def _get_breadcrumb_url(cls, kwargs, view):
        keys = re.findall("<([^>]+)>", cls.get_url_patterns()[0])
        kw = {k: v for (k, v) in kwargs.items() if k in keys}
        url = reverse("navigator:" + cls.get_view_name(), kwargs=kw)
        return url

    @classmethod
    def _get_breadcrumb_name(cls, kwargs, view):
        """Return the name of this 'level' in the breadcrumb trail"""
        if hasattr(cls, 'url_fragment'):
            return cls.url_fragment.title()
        elif issubclass(cls, ListView):
            return cls.get_model_name()
        else:
            obj = cls._get_object(kwargs)
            return "{obj.id} : {obj}".format(**locals())

    @classmethod
    def _get_breadcrumbs(cls, kwargs, view):
        breadcrumbs = (cls.parent._get_breadcrumbs(kwargs, view)
                       if cls.parent else [])
        url = cls._get_breadcrumb_url(kwargs, view)
        name = cls._get_breadcrumb_name(kwargs, view)
        breadcrumbs.append((name, url))
        return breadcrumbs


class BaseMixin(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin):

    """Base mixin for a project view with hierarchy and bread crumbs"""
    pass


class ProjectDetailView(BaseMixin, DetailView):
    pass


class ProjectListBaseView(BaseMixin, ListView):
    pass


class ProjectScriptView(BaseMixin, ScriptView):

    """
    View that provides access to a Script from within a plugin.
    Subclasses should provide a script instance.
    """
    template_name = "project/script_base.html"
    script = None

    def form_valid(self, form):
        result = super(ProjectScriptView, self).form_valid(form)
        if self.success:
            message = self.success_message(result)
            self.request.session['notification'] = message
        return result

    def get_success_url(self):
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def get_cancel_url(self):
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def get_context_data(self, **kwargs):
        context = super(ProjectScriptView, self).get_context_data(**kwargs)
        context["script_doc"] = (self.script.__doc__ and self.script.__doc__.replace("   ", ""))
        context["cancel_url"] = self.get_cancel_url()
        return context

    def success_message(self, result=None):
        """Message to display (notify) on success"""
        return ("Succesfully ran action {self.script.__name__}"
                .format(**locals()))


class ProjectFormView(BaseMixin, FormView):
    template_name = "project/form_base.html"

    def get_success_url(self):
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def get_cancel_url(self):
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def get_context_data(self, **kwargs):
        context = super(ProjectFormView, self).get_context_data(**kwargs)
        context["cancel_url"] = self.get_cancel_url()
        return context


class ProjectActionRedirectView(BaseMixin, RedirectView):
    permanent = False
    # we don't want the browser to cache the redirect and prevent the action
    # (but what we really want is a POST request instead???)
    required_project_permission = authorisation.ROLE_PROJECT_WRITER

    def get(self, request, *args, **kwargs):
        result = self.action(**kwargs)
        message = self.success_message(result)
        request.session['notification'] = message
        return (super(ProjectActionRedirectView, self)
                .get(request, *args, **kwargs))

    def get_redirect_url(self, **kargs):
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def action(self, **kwargs):
        """Perform the intended action. Kwargs are the url parameters"""
        raise NotImplementedError()

    def success_message(self, result=None):
        """Message to display (notify) on success"""
        # TODO: refactor the copy paste (also redirect/success url)
        return ("Succesfully ran action {self.__class__.__name__}"
                .format(**locals()))


class ProjectEditView(BaseMixin, UpdateView):
    url_fragment = 'edit'

    def get_success_url(self):
        self.request.session['notification'] = "Successfully edited object"
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def get_form(self, form_class=None):
        form = super(ProjectEditView, self).get_form(form_class)
        if 'project' in form.fields:
            form.fields['project'].queryset = Project.objects.filter(
                projectrole__user=self.request.user,
                projectrole__role_id__gte=PROJECT_ROLES.WRITER.value)
        return form

    def get_cancel_url(self):
        return self.parent._get_breadcrumb_url(self.kwargs, self)

    def get_context_data(self, **kwargs):
        context = super(ProjectEditView, self).get_context_data(**kwargs)
        context["cancel_url"] = self.get_cancel_url()
        return context
