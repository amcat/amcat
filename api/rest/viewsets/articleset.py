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
from rest_framework import serializers
from amcat.models import ArticleSet
from amcat.tools import amcates
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets.project import ProjectViewSetMixin
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from api.rest.viewset import AmCATViewSetMixin

__all__ = (
    "ArticleSetSerializer", "ArticleSetViewSet", "FavouriteArticleSetViewSet",
    "CodingjobArticleSetViewSet")

class ArticleSetSerializer(AmCATModelSerializer):
    favourite = serializers.SerializerMethodField("is_favourite")
    articles = serializers.SerializerMethodField("n_articles")

    @property
    def project(self):
        try:
            return self.context["view"].project
        except AttributeError:
            pass

    @cached
    def get_favourite_articlesets(self):
        if not self.project: return set()
        return set(self.project.favourite_articlesets.all().values_list("id", flat=True))

    @cached
    def get_nn(self):
        view = self.context["view"]
        if hasattr(view, 'object_list'):
            sets = list(view.object_list.values_list("id", flat=True))
        else:
            sets = [view.object.id]
        return dict(amcates.ES().aggregate_query(filters={'sets' : sets}, group_by='sets'))

    def n_articles(self, articleset):
        if not articleset: return None
        return self.get_nn().get(articleset.id)

    def is_favourite(self, articleset):
        if not articleset or not self.project: return None
        return articleset.id in self.get_favourite_articlesets()

    def restore_fields(self, data, files):
        data = data.copy() # make data mutable
        if 'project' not in data:
            data['project'] = self.context['view'].project.id
        return super(ArticleSetSerializer, self).restore_fields(data, files)
            
    class Meta:
        model = ArticleSet


class _NoProjectRequestedError(ValueError): pass

class ArticleSetViewSetMixin(AmCATViewSetMixin):
    model_key = "articleset"
    model = ArticleSet
    search_fields = ordering_fields = ("id", "name", "provenance")

class ArticleSetViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin, ModelViewSet):
    model_serializer_class = ArticleSetSerializer
    model = ArticleSet
    
    def filter_queryset(self, queryset):
        queryset = super(ArticleSetViewSet, self).filter_queryset(queryset)
        return queryset.filter(id__in=self.project.all_articlesets())

class FavouriteArticleSetViewSetMixin(AmCATViewSetMixin):
    model_key = "favourite_articleset"
    base_name = "favourite_articleset"
    search_fields = ordering_fields = ("id", "name", "provenance")
    model = ArticleSet

class FavouriteArticleSetViewSet(ProjectViewSetMixin, FavouriteArticleSetViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model_serializer_class = ArticleSetSerializer
    model_key = "favourite_articleset"
    model = ArticleSet


    def filter_queryset(self, queryset):
        queryset = super(FavouriteArticleSetViewSet, self).filter_queryset(queryset)
        return queryset.filter(id__in=self.project.favourite_articlesets.all())

    def get_url(cls, base_name=None, view='list', **kwargs):
        return super(FavouriteArticleSetViewSet, cls).get_url(base_name=cls.base_name, view=view, **kwargs)

class CodingjobArticleSetViewSetMixin(AmCATViewSetMixin):
    model_key = "codingjob_articleset"
    base_name = "codingjob_articleset"
    search_fields = ordering_fields = ("id", "name", "provenance")
    model = ArticleSet


class CodingjobArticleSetViewSet(ProjectViewSetMixin, CodingjobArticleSetViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model_serializer_class = ArticleSetSerializer
    model_key = "codingjob_articleset"
    model = ArticleSet

    def filter_queryset(self, queryset):
        queryset = super(CodingjobArticleSetViewSet, self).filter_queryset(queryset)
        return queryset.filter(id__in=self.project.all_articlesets(), codingjob_set__id__isnull=False)

    def get_url(cls, base_name=None, view='list', **kwargs):
        return super(CodingjobArticleSetViewSet, cls).get_url(base_name=cls.base_name, view=view, **kwargs)
