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

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin, ProjectScriptView
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
    
class ArticleSetListView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, DatatableMixin, ListView):
    model = ArticleSet
    parent = ProjectDetailsView
    context_category = 'Articles'
    rowlink = './{id}'

    @classmethod
    def get_url_patterns(cls):
        patterns = list(super(ArticleSetListView, cls).get_url_patterns())
        patterns.append(patterns[0][:-1] + "(?P<what>[a-z]+)/?$")
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
    model = ArticleSet
    context_category = 'Articles'
        
    resource = SearchResource
    rowlink = './{id}'
    
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


class ImportSetView(ProjectScriptView):
    script = ImportSet
    parent = ArticleSetListView
    model = ArticleSet


    def get_success_url(self):
        project = self.form.cleaned_data["target_project"]
        return reverse(ArticleSetListView.get_view_name(), kwargs={"project_id":project.id})

    def get_form(self, form_class):
        form = super(ImportSetView, self).get_form(form_class)
        if self.request.method == 'GET':
            # list current users favourite projects but exclude already imported and currect project
            qs = Project.objects.filter(favourite_users=self.request.user.get_profile())
            qs = qs.exclude(articlesets=self.kwargs["articleset_id"])
            qs = qs.exclude(pk=self.project.id)
            form.fields['target_project'].queryset = qs
            form.fields['target_project'].help_text = "Only showing your favourite projects that do not use this set already"

        return form


class SampleSetView(ProjectScriptView):
    parent = ArticleSetDetailsView
    model = ArticleSet
    script = SampleSet
    url_fragment = 'sample'
    context_category = 'Articles'
    
    def get_success_url(self):
        return reverse("article set-list", args=[self.project.id])

        
class RefreshArticleSetView(RedirectView):
    def get_redirect_url(self, projectid, pk):
        # refresh the queryset. Probably not the nicest way to do this (?)
        ArticleSet.objects.get(pk=pk).refresh_index(full_refresh=True)
        return reverse("article set-details", args=[projectid, pk])

from amcat.models import Role
PROJECT_READ_WRITE = Role.objects.get(projectlevel=True, label="read/write").id
class EditSetView(HierarchicalViewMixin, ProjectViewMixin, BreadCrumbMixin, UpdateView):
    parent = ArticleSetDetailsView
    model = ArticleSet
    url_fragment = 'edit'
    context_category = 'Articles'
    fields = ['project', 'name', 'provenance']
    
    def get_success_url(self):
        return reverse("article set-details", args=[self.project.id, self.object.id])
    def get_form(self, form_class):
        form = super(EditSetView, self).get_form(form_class)
        form.fields['project'].queryset = Project.objects.filter(projectrole__user=self.request.user,
                                                                 projectrole__role_id__gte=PROJECT_READ_WRITE)
        return form
    
