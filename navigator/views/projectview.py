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

from django.views.generic.base import ContextMixin, TemplateResponseMixin, TemplateView
from django.views.generic.edit import CreateView
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory


from api.rest import resources
from api.rest.datatable import Datatable

from amcat.models import authorisation, Project
from django.core.exceptions import PermissionDenied

class BreadCrumbMixin(object):
    def get_context_data(self, **kwargs):
        context = super(BreadCrumbMixin, self).get_context_data(**kwargs)
        context["breadcrumbs"] = list(self.get_breadcrumbs())
        return context

    def get_breadcrumbs(self):
        bc = self._get_breadcrumbs(self.kwargs)
        return bc
        
    def _get_breadcrumbs(cls, kwargs):
        return []
        
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
    project_id_url_kwarg = 'project_id'
    required_project_permission = authorisation.ROLE_PROJECT_METAREADER
    context_category = None
    
    def get_context_data(self, **kwargs):
        context = super(ProjectViewMixin, self).get_context_data(**kwargs)
        context["project"] = self.project
        context["context"] = self.project # for menu / backwards compat.

        context["main_active"] = 'Projects'
        context["context_category"] = self.context_category
        return context
    
    def get_project(self):
        kwarg = self.project_id_url_kwarg
        x = self.kwargs
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


    def get_breadcrumbs(self):
        bc = self._get_breadcrumbs(self.kwargs)
        bc.insert(0, ("Projects", reverse("projects")))
        bc.insert(1, ("{self.project.id} : {self.project}".format(**locals()),
                      reverse("project", args=(self.project.id, ))))
        return bc
        
    def get_template_names(self):
        
        if self.template_name is not None:
            return [self.template_name]
        else:
            name = re.sub("[- ]", "_", self.get_view_name())
            return ["project/{name}.html".format(**locals())]
        
from django.views.generic.list import ListView

class HierarchicalViewMixin(object):

    @property
    def pk_url_kwarg(self):
        return self.get_model_key()

    @classmethod
    def get_model_key(cls):
        return cls.model._meta.get_field("id").db_column

    @classmethod
    def get_model_name(cls):
        return cls.model._meta.verbose_name_plural.title()
        
    @classmethod
    def get_table_name(cls):
        return cls.model._meta.db_table

    @classmethod
    def _get_object(cls, kwargs):
        pk = kwargs[cls.get_model_key()]
        return cls.model.objects.get(pk=pk)
        
    
    @classmethod
    def get_view_name(cls):
        name = cls.model._meta.verbose_name
        if hasattr(cls, 'url_fragment'):
            name += "-" + cls.url_fragment
        else:
            name += ("-list" if issubclass(cls, ListView) else "-details")

        return name
        
    @classmethod
    def get_url_patterns(cls):
        comps = cls._get_url_components()
        return ["^" + "/".join(comps) + "/$"]

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

        if hasattr(cls, 'url_fragment'):
            yield cls.url_fragment
        elif issubclass(cls, ListView):
            yield cls.get_table_name().lower()
        else:
            yield "(?P<{key}>[0-9]+)".format(key=cls.get_model_key())

    @classmethod
    def _get_breadcrumbs(cls, kwargs):
        breadcrumbs = cls.parent._get_breadcrumbs(kwargs) if cls.parent else []
        
        keys = re.findall("<([^>]+)>", cls.get_url_patterns()[0])
        kw = {k:v for (k,v) in kwargs.items() if k in keys}
        url = reverse(cls.get_view_name(), kwargs=kw)

        if hasattr(cls, 'url_fragment'):
            name = cls.url_fragment.title()
        elif issubclass(cls, ListView):
            name = cls.get_model_name()
        else:
            obj = cls._get_object(kwargs)
            name = "{obj.id} : {obj}".format(**locals())
            
        breadcrumbs.append((name, url))
        return breadcrumbs
        
        
from navigator.views.scriptview import ScriptView
class ProjectScriptView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, ScriptView):
    """
    View that provides access to a Script from within a plugin.
    Subclasses should provide a script instance.
    """
    template_name = "project/script_base.html"
    script = None

    def get_success_url(self):
        return reverse("project", kwargs=dict(id=self.project.id))
        
    def get_context_data(self, **kwargs):
        context = super(ProjectScriptView, self).get_context_data(**kwargs)
        context["script_doc"] = self.script.__doc__ and self.script.__doc__.strip()
        return context

        
