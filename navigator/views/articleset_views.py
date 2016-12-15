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

import datetime
import json

from django import forms
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.widgets import HiddenInput
from django.http import Http404
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from amcat.models import Article
from amcat.models import Project, ArticleSet
from amcat.models.project import LITTER_PROJECT_ID
from amcat.scripts.actions.deduplicate_set import DeduplicateSet
from amcat.scripts.actions.import_articleset import ImportSet
from amcat.scripts.actions.sample_articleset import SampleSet
from amcat.tools.amcates import ES
from api.rest.resources import SearchResource
from api.rest.viewsets import FavouriteArticleSetViewSet, ArticleSetViewSet, CodingjobArticleSetViewSet
from navigator.views.datatableview import DatatableMixin
from navigator.views.project_views import ProjectDetailsView
from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView, ProjectActionRedirectView, ProjectEditView

UPLOAD_PLUGIN_TYPE = 1

from django.utils.safestring import SafeText
from django.template.defaultfilters import escape
from django.http import HttpResponseBadRequest, HttpResponse


class ArticleSetListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = ArticleSet
    parent = ProjectDetailsView
    context_category = 'Articles'
    rowlink = './{id}'

    def get(self, *args, **kargs):
        favaction = self.request.GET.get('favaction')
        if favaction is not None:
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
        patterns.append(patterns[0][:-1] + "(?P<what>|active|archived|coding)?/?$")
        return patterns

    @property
    def what(self):
        default = "active" if self.project.favourite_articlesets.exists() else "archived"
        return self.kwargs.get("what", default)

    def get_context_data(self, **kwargs):
        context = super(ArticleSetListView, self).get_context_data(**kwargs)
        tables = [
            ("favourite", '<i class="icon-star"></i> <b>Favourites</b>'),
            ("archived", "Archived Sets"),
            ("codingjob", "Coding Job Sets"),
        ]
        what = self.what
        if not ArticleSet.objects.filter(Q(projects_set=self.project)
                                         | Q(project=self.project)).exists():
            no_sets = True
        if not self.project.favourite_articlesets.exists():
            no_active = True
        favaction = "unsetfav" if what == 'active' else "setfav"

        context.update(locals())
        return context

    def get_resource(self):
        if self.what == "active":
            return FavouriteArticleSetViewSet
        elif self.what == "coding":
            return CodingjobArticleSetViewSet
        else:
            return ArticleSetViewSet

    def filter_table(self, table):
        if self.what == 'archived':
            sets = ArticleSet.objects.filter(Q(projects_set=self.project) | Q(project=self.project))
            sets = sets.filter(codingjob_set__isnull=True)
            sets = sets.exclude(id__in=self.project.favourite_articlesets.all())
            sets = list(sets.values_list("pk", flat=True))
            table = table.filter(pk__in=sets)

        table = table.rowlink_reverse('navigator:articleset-details', args=[self.project.id, '{id}'])
        table = table.hide("project")
        table = table.hide("favourite")
        table = table.hide("featured")
        return table

    def get_datatable_kwargs(self):
        return {
            "url_kwargs": {
                "project": self.project.id
            },
            "checkboxes": True
        }


class ArticleSetArticleDeleteForm(forms.Form):
    articles = forms.ModelMultipleChoiceField(queryset=Article.objects.none())

    def __init__(self, articleset, *args, **kwargs):
        super(ArticleSetArticleDeleteForm, self).__init__(*args, **kwargs)
        self.fields['articles'].queryset = articleset.articles.only("id").all()
        self.articleset = articleset

    def save(self):
        self.articleset.remove_articles(self.cleaned_data["articles"])


class AddArticlesToArticleSetForm(forms.Form):
    articlesets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.none())
    articles = forms.ModelMultipleChoiceField(queryset=Article.objects.none())

    def __init__(self, project, articleset, *args, **kwargs):
        super(AddArticlesToArticleSetForm, self).__init__(*args, **kwargs)
        self.fields["articlesets"].queryset = project.articlesets_set.only("id").all()
        self.fields["articles"].queryset = articleset.articles.only("id").all()

    def save(self):
        for aset in self.cleaned_data["articlesets"]:
            aset.add_articles(self.cleaned_data["articles"])

    
class ArticleSetDetailsView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, DetailView):
    parent = ArticleSetListView
    resource = SearchResource
    rowlink = './{id}'
    model = ArticleSet

    def delete(self, request, project, articleset):
        """Accepts a list of article ids as post argument (articles)."""
        if not self.can_edit():
            raise PermissionDenied("You can't edit this articleset.")

        articleset = ArticleSet.objects.get(id=articleset, project__id=project)
        form = ArticleSetArticleDeleteForm(articleset=articleset, data=request.POST)

        if form.is_valid():
            form.save()
            ES().refresh()
            return HttpResponse("OK", status=200)

        return HttpResponseBadRequest(str(dict(form.errors)))

    def post(self, request, project, articleset):
        if not self.can_edit():
            raise PermissionDenied("You can't edit this articleset.")

        articleset = ArticleSet.objects.get(id=articleset, project__id=project)
        form = AddArticlesToArticleSetForm(project=self.project, articleset=articleset, data=request.POST)

        if form.is_valid():
            form.save()
            return HttpResponse("OK", status=200)

        return HttpResponseBadRequest(str(dict(form.errors)))
    
    def get_datatable_kwargs(self):
        return {"checkboxes": True}

    def filter_table(self, table):
        return table.filter(sets=self.object.id, project=self.project.id)

    def get_context_data(self, **kwargs):
        context = super(ArticleSetDetailsView, self).get_context_data(**kwargs)
        
        if not ((self.object.project_id == self.project.id) or
                self.project.articlesets.filter(pk=self.object.id).exists()):
            raise Http404("ArticleSet {self.object.id}:{self.object} does not exist in project {self.project.id}: {self.project}"
                          .format(**locals()))

        star = self.request.GET.get("star")
        starred = self.project.favourite_articlesets.filter(pk=self.object.id).exists()
        if star is not None:
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
        return reverse("navigator:" + ArticleSetListView.get_view_name(), kwargs={"project":project.id})

    def get_form(self, form_class):
        form = super(ArticleSetImportView, self).get_form(form_class)
        if self.request.method == 'GET':
            # list current users favourite projects but exclude already imported and currect project
            qs = Project.objects.filter(favourite_users=self.request.user.userprofile)
            qs = qs.exclude(articlesets=self.kwargs["articleset"])
            qs = qs.exclude(pk=self.project.id)
            form.fields['target_project'].queryset = qs
            form.fields['target_project'].help_text = "Only showing your favourite projects that do not use this set already"
            form.fields['articleset'].queryset = ArticleSet.objects.filter(pk=self.kwargs['articleset'])
        return form

    def get_initial(self):
        initial = super().get_initial()
        initial['articleset'] = self.kwargs['articleset']
        return initial

class ArticleSetSampleView(ProjectScriptView):
    parent = ArticleSetDetailsView
    script = SampleSet
    url_fragment = 'sample'

    def get_success_url(self):
        return self.parent._get_breadcrumb_url({'project' : self.project.id, 'articleset' : self.result.id}, self)

    def get_form_kwargs(self):
        kwargs = super(ArticleSetSampleView, self).get_form_kwargs()
        kwargs['project'] = self.project
        return kwargs
    def success_message(self, result=None):
        old = ArticleSet.objects.get(pk=self.kwargs['articleset'])
        old_name = escape(old.name)
        new_name = escape(self.result.name)
        old_url = reverse('navigator:articleset-details', kwargs=self.kwargs)
        return SafeText("""Created sample set {new_name} as shown below.
                            <a href='{old_url}'>Return to original set {old.id}: {old_name}</a>"""
                            .format(**locals()))

class ArticleSetDeduplicateView(ProjectScriptView):
    parent = ArticleSetDetailsView
    script = DeduplicateSet
    url_fragment = "deduplicate"


    def get_form(self, form_class):
        form = super(ArticleSetDeduplicateView, self).get_form(form_class)
        form.fields["articleset"].widget = HiddenInput()
        form.fields["articleset"].initial = self.get_object()
        return form

    def success_message(self, result=None):
        (n, dry_run) = self.result
        if not n:
            return SafeText("No duplicates were found in the set")
        if dry_run:
            return SafeText("Found {n} duplicates, but did not delete them. Re-run without dry-run to remove"
                            .format(**locals()))
        else:
            return SafeText("Removed {n} duplicates from the set!"
                            .format(**locals()))
    

class ArticleSetEditView(ProjectEditView):
    parent = ArticleSetDetailsView
    fields = ['project', 'name', 'provenance']


class ArticleSetCreateView(HierarchicalViewMixin, ProjectViewMixin, CreateView):
    parent = ArticleSetListView
    fields = ['project', 'name', 'provenance']
    url_fragment = 'create' 
    model = ArticleSet

    def get_form(self, form_class):
        if self.request.method == 'GET':
            return form_class(initial={'project': self.project})
        else:
            return super(ArticleSetCreateView, self).get_form(form_class)

    def get_success_url(self):
        return reverse("navigator:articleset-details", args=[self.project.id, self.object.id])


class MultipleArticleSetDestinationView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    """
    If a user selected multiple articlesets upon uploading, (s)he will be redirected here for
    an overview of those sets.
    """
    model = ArticleSet
    parent = ArticleSetListView
    context_category = 'Articles'
    rowlink = './../{id}'
    url_fragment = 'multiple'

    def filter_table(self, table):
        return table.filter(pk=self.request.GET.getlist('set'), project=self.project)


class ArticleSetRefreshView(ProjectActionRedirectView):
    parent = ArticleSetDetailsView
    url_fragment = "refresh"

    def action(self, articleset, **kwargs):
        # refresh the queryset. Probably not the nicest way to do this (?)
        ArticleSet.objects.get(pk=articleset).refresh_index(full_refresh=True)


        
class ArticleSetDeleteView(ProjectActionRedirectView):
    parent = ArticleSetDetailsView
    url_fragment = "delete"

    def action(self, project, articleset):
        aset = ArticleSet.objects.get(pk=articleset)
        project = Project.objects.get(pk=project)
        aset.project = Project.objects.get(id=LITTER_PROJECT_ID)
        aset.indexed = False
        aset.provenance = json.dumps({
            "provenance": aset.provenance,
            "project": project.id,
            "deleted_on": datetime.datetime.now().isoformat()
        })
        aset.save()
        project.favourite_articlesets.remove(aset)

    def get_redirect_url(self, **kwargs):
        return ArticleSetListView._get_breadcrumb_url(kwargs, self)

class ArticleSetUnlinkView(ProjectActionRedirectView):
    parent = ArticleSetDetailsView
    url_fragment = "unlink"

    def action(self, project, articleset):
        aset = ArticleSet.objects.get(pk=articleset)
        project = Project.objects.get(pk=project)
        project.articlesets.remove(aset)
        project.favourite_articlesets.remove(aset)

    def get_redirect_url(self, **kwargs):
        return ArticleSetListView._get_breadcrumb_url(kwargs, self)
