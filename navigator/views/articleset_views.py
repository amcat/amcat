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

from django.core.urlresolvers import reverse

from amcat.scripts.actions.sample_articleset import SampleSet
from amcat.scripts.actions.import_articleset import ImportSet
from api.rest.viewsets import FavouriteArticleSetViewSet, ArticleSetViewSet, CodingjobArticleSetViewSet

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectActionRedirectView, ProjectEditView
from navigator.views.datatableview import DatatableMixin
from amcat.models import Project, ArticleSet
from api.rest.resources import SearchResource
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import UpdateView

from django.views.generic.base import RedirectView
from django.db.models import Q
from navigator.views.project_views import ProjectDetailsView


from api.rest.datatable import FavouriteDatatable
from django.utils.safestring import SafeText
from django.template.defaultfilters import escape


class ArticleSetListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = ArticleSet
    parent = ProjectDetailsView
    context_category = 'Articles'
    rowlink = './{id}'

    @classmethod
    def get_url_patterns(cls):
        patterns = list(super(ArticleSetListView, cls).get_url_patterns())
        patterns.append(patterns[0][:-1] + "(?P<what>|favourites|own|linked|coding)?/?$")
        return patterns

    @property
    def what(self):
        return self.kwargs.get("what", "favourites")

    def get_context_data(self, **kwargs):
        context = super(ArticleSetListView, self).get_context_data(**kwargs)
        tables = [("favourite", '<i class="icon-star"></i> <b>Favourites</b>'),
                  ("own", "Own Sets"),
                  ("linked", "Linked Sets"),
                  ("codingjob", "Coding Job Sets"),
                  ]
        context.update(locals())
        context.update({"what" : self.what})
        return context

    def filter_linked_table(self, table):
        return table.filter(projects_set=self.project)

    def filter_own_table(self, table):
        return table.filter(project=self.project, codingjob_set__id='null')

    def get_resource(self):
        if self.what == "favourites":
            return FavouriteArticleSetViewSet
        elif self.what == "coding":
            return CodingjobArticleSetViewSet
        else:
            return ArticleSetViewSet

    def filter_table(self, table):
        return getattr(self, "filter_{}_table".format(self.what), lambda t : t)(table)


    def get_datatable(self):
        """Create the Datatable object"""
        url = reverse('article set-details', args=[self.project.id, 123])
        table = FavouriteDatatable(resource=self.get_resource(), label="article set",
                                   set_url=url + "?star=1", unset_url=url+"?star=0",
                                   url_kwargs={"project" : self.project.id})
        table = table.rowlink_reverse('article set-details', args=[self.project.id, '{id}'])
        table = table.hide("project")
        table = self.filter_table(table)
        return table



class ArticleSetDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, DetailView):
    parent = ArticleSetListView
    resource = SearchResource
    rowlink = './{id}'
    model = ArticleSet

    def filter_table(self, table):
        return table.filter(sets=self.object.id)

    def get_context_data(self, **kwargs):
        context = super(ArticleSetDetailsView, self).get_context_data(**kwargs)

        star = self.request.GET.get("star")
        starred = self.project.favourite_articlesets.filter(pk=self.object.id).exists()
        if (star is not None):
            if bool(int(star)) != starred:
                starred = not starred
                if starred:
                    self.project.favourite_articlesets.add(self.object.id)
                else:
                    self.project.favourite_articlesets.remove(self.object.id)
        context['starred'] = starred
        return context


class ArticleSetImportView(ProjectScriptView):
    script = ImportSet
    parent = ArticleSetDetailsView
    url_fragment = 'import'

    def get_success_url(self):
        project = self.form.cleaned_data["target_project"]
        return reverse(ArticleSetListView.get_view_name(), kwargs={"project_id":project.id})

    def get_form(self, form_class):
        form = super(ArticleSetImportView, self).get_form(form_class)
        if self.request.method == 'GET':
            # list current users favourite projects but exclude already imported and currect project
            qs = Project.objects.filter(favourite_users=self.request.user.get_profile())
            qs = qs.exclude(articlesets=self.kwargs["articleset_id"])
            qs = qs.exclude(pk=self.project.id)
            form.fields['target_project'].queryset = qs
            form.fields['target_project'].help_text = "Only showing your favourite projects that do not use this set already"

        return form


class ArticleSetSampleView(ProjectScriptView):
    parent = ArticleSetDetailsView
    script = SampleSet
    url_fragment = 'sample'

    def get_success_url(self):
        return self.parent._get_breadcrumb_url({'project_id' : self.project.id, 'articleset_id' : self.result.id}, self)


    def success_message(self, result=None):
        old = ArticleSet.objects.get(pk=self.kwargs['articleset_id'])
        return SafeText("Created sample set {newname} as shown below. "
                        "<a href='{oldurl}'>Return to original set {old.id} : {oldname}</a>"
                        .format(newname=escape(self.result.name), oldurl=reverse('article set-details', kwargs=self.kwargs),
                                oldname=escape(old.name), **locals()))

from amcat.models import Role
PROJECT_READ_WRITE = 12
# Role.objects.get(projectlevel=True, label="read/write").id
class ArticleSetEditView(ProjectEditView):
    parent = ArticleSetDetailsView
    fields = ['project', 'name', 'provenance']


from amcat.models import Plugin
from api.rest.resources import PluginResource
UPLOAD_PLUGIN_TYPE=1

class ArticleSetUploadListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    parent = ArticleSetListView
    model = Plugin
    resource = PluginResource
    view_name = "article set-upload-list"
    url_fragment = "upload"

    def filter_table(self, table):
        table = table.rowlink_reverse('article set-upload', args=[self.project.id, '{id}'])
        return table.filter(plugin_type=UPLOAD_PLUGIN_TYPE).hide('id', 'class_name')#, 'plugin_type')

class ArticleSetUploadView(ProjectScriptView):
    parent = ArticleSetUploadListView
    view_name = "article set-upload"
    template_name = "project/article_set_upload.html"

    def get_script(self):
        return Plugin.objects.get(pk=self.kwargs['plugin_id']).get_class()

    def get_form(self, form_class):
        if self.request.method == 'GET':
            return form_class.get_empty(project=self.project)
        else:
            return super(ArticleSetUploadView, self).get_form(form_class)

    def form_valid(self, form):
        self.run_form(form)
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        self.script = self.get_script()
        context = super(ArticleSetUploadView, self).get_context_data(**kwargs)
        if getattr(self, 'success', False):
            context['created_set'] = self.script_object.articleset
            context['created_n'] = len(self.result)

        return context

class ArticleSetRefreshView(ProjectActionRedirectView):
    parent = ArticleSetDetailsView
    url_fragment = "refresh"

    def action(self, project_id, articleset_id):
        # refresh the queryset. Probably not the nicest way to do this (?)
        ArticleSet.objects.get(pk=articleset_id).refresh_index(full_refresh=True)

from amcat.models.project import LITTER_PROJECT_ID
import json, datetime
class ArticleSetDeleteView(ProjectActionRedirectView):
    parent = ArticleSetDetailsView
    url_fragment = "delete"

    def action(self, project_id, articleset_id):
        aset = ArticleSet.objects.get(pk=articleset_id)
        project = Project.objects.get(pk=project_id)

        aset.project = Project.objects.get(id=LITTER_PROJECT_ID)
        aset.indexed = False
        aset.provenance = json.dumps({
            "provenance" : aset.provenance,
            "project" : project.id,
            "deleted_on" : datetime.datetime.now().isoformat()
        })
        aset.save()
        project.favourite_articlesets.remove(aset)

    def get_redirect_url(self, **kwargs):
        return ArticleSetListView._get_breadcrumb_url(kwargs, self)

class ArticleSetUnlinkView(ProjectActionRedirectView):
    parent = ArticleSetDetailsView
    url_fragment = "unlink"

    def action(self, project_id, articleset_id):
        aset = ArticleSet.objects.get(pk=articleset_id)
        project = Project.objects.get(pk=project_id)
        project.articlesets.remove(aset)
        project.favourite_articlesets.remove(aset)

    def get_redirect_url(self, **kwargs):
        return ArticleSetListView._get_breadcrumb_url(kwargs, self)
