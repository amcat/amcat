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

import json
import datetime

from django.core.urlresolvers import reverse
from django.db.models import Q
from api.rest.resources import PluginResource

from amcat.models import Plugin
from amcat.models.project import LITTER_PROJECT_ID

from amcat.scripts.actions.sample_articleset import SampleSet
from amcat.scripts.actions.import_articleset import ImportSet
from api.rest.viewsets import FavouriteArticleSetViewSet, ArticleSetViewSet, CodingjobArticleSetViewSet

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectActionRedirectView, ProjectEditView
from navigator.views.scriptview import ScriptHandler

from navigator.views.datatableview import DatatableMixin
from amcat.models import Project, ArticleSet
from api.rest.resources import SearchResource
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from navigator.views.project_views import ProjectDetailsView
UPLOAD_PLUGIN_TYPE = 1

from django.utils.safestring import SafeText
from django.template.defaultfilters import escape


class ArticleSetListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = ArticleSet
    parent = ProjectDetailsView
    context_category = 'Articles'
    rowlink = './{id}'



    def get(self, *args, **kargs):
        favaction = self.request.GET.get('favaction')
        if (favaction is not None):
            ids = {int(id) for id in self.request.GET.getlist('ids')}
            favs = self.project.favourite_articlesets
            favids = set(favs.values_list("pk", flat=True))
            if favaction == "setfav":
                ids -= favids
                func = favs.add
            else:
                ids &= favids
                func = favs.remove
            if ids:
                [func(id) for id in ids]

        return super(ArticleSetListView, self).get(*args, **kargs)

    @classmethod
    def get_url_patterns(cls):
        patterns = list(super(ArticleSetListView, cls).get_url_patterns())
        patterns.append(patterns[0][:-1] + "(?P<what>|favourites|archived|coding)?/?$")
        return patterns

    @property
    def what(self):
        default = "favourites" if self.project.favourite_articlesets.exists() else "archived"
        return self.kwargs.get("what", default)

    def get_context_data(self, **kwargs):
        context = super(ArticleSetListView, self).get_context_data(**kwargs)
        tables = [("favourite", '<i class="icon-star"></i> <b>Favourites</b>'),
                  ("archived", "Archived Sets"),
                  ("codingjob", "Coding Job Sets"),
                  ]
        what = self.what
        if not ArticleSet.objects.filter(Q(projects_set=self.project)
                                         | Q(project=self.project)).exists():
            no_sets = True
        if not self.project.favourite_articlesets.exists():
            no_favourites = True

        if what == 'favourites':
            favaction_label = "Archive selected sets"
            favaction = "unsetfav"
        else:
            favaction_label = "Make selected sets favourite"
            favaction ="setfav"

        context.update(locals())
        return context

    def get_resource(self):
        if self.what == "favourites":
            return FavouriteArticleSetViewSet
        elif self.what == "coding":
            return CodingjobArticleSetViewSet
        else:
            return ArticleSetViewSet

    def filter_table(self, table):
        print(type(table))
        if self.what == 'archived':
            sets = ArticleSet.objects.filter(Q(projects_set=self.project) | Q(project=self.project))
            sets = sets.filter(codingjob_set__isnull=True)
            sets = sets.exclude(id__in=self.project.favourite_articlesets.all())

            sets = list(sets.values_list("pk", flat=True))
            table = table.filter(pk__in=sets)

        table = table.rowlink_reverse('article set-details', args=[self.project.id, '{id}'])
        table = table.hide("project")
        table = table.hide("favourite")
        return table

    def get_datatable_kwargs(self):
        return {"url_kwargs": {"project" : self.project.id}}




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

class ArticleSetEditView(ProjectEditView):
    parent = ArticleSetDetailsView
    fields = ['project', 'name', 'provenance']



class ArticleSetUploadListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    parent = ArticleSetListView
    model = Plugin
    resource = PluginResource
    view_name = "article set-upload-list"
    url_fragment = "upload"

    def filter_table(self, table):
        table = table.rowlink_reverse('article set-upload', args=[self.project.id, '{id}'])
        return table.filter(plugin_type=UPLOAD_PLUGIN_TYPE).hide('id', 'class_name')#, 'plugin_type')

class ArticleSetRedirectHandler(ScriptHandler):
    def get_redirect(self):
        setid = self.task._get_raw_result()
        return reverse("article set-details", args=[self.task.project.id, setid]), "View Set"

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
        return self.run_form_delayed(self.project, handler=ArticleSetRedirectHandler)

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
