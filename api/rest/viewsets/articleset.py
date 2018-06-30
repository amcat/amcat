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
from collections import OrderedDict

from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from amcat.models import ArticleSet, ProjectArticleset, , PROJECT_ROLES, ROLE_PROJECT_ADMIN
from amcat.tools.aggregate_es.aggregate import aggregate
from amcat.tools.aggregate_es.categories import ArticlesetCategory
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATProjectModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin

from rest_framework import status
from rest_framework.response import Response

__all__ = (
    "ArticleSetSerializer", "ArticleSetViewSet", "FavouriteArticleSetViewSet",
    "CodingjobArticleSetViewSet")

        
class ArticleSetSerializer(AmCATProjectModelSerializer):
    favourite = serializers.SerializerMethodField("is_favourite")
    articles = serializers.SerializerMethodField("n_articles")


    @cached
    def get_favourite_articlesets(self):
        if not self.project: return set()
        return set(self.project.favourite_articlesets.all().values_list("id", flat=True))

    @cached
    def get_nn(self):
        try:
            set_ids = [s.id for s in self.instance]
        except TypeError:
            set_ids = [self.instance.id]
        category = ArticlesetCategory(ArticleSet.objects.filter(id__in=set_ids))
        return dict(aggregate(filters={'sets': set_ids}, categories=[category], objects=False))

    def n_articles(self, articleset):
        if not articleset: return None
        return self.get_nn().get(articleset.id, 0)

    def is_favourite(self, articleset):
        if not articleset or not self.project: return None
        return articleset.id in self.get_favourite_articlesets()


    class Meta:
        model = ArticleSet
        fields = "__all__"

class _NoProjectRequestedError(ValueError): pass

class ArticleSetViewSetMixin(AmCATViewSetMixin):
    model_key = "articleset"
    model = ArticleSet
    search_fields = ordering_fields = ("id", "name", "provenance")
    queryset = ArticleSet.objects.all()

class ArticleSetViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin, ModelViewSet):
    serializer_class = ArticleSetSerializer
    model = ArticleSet
    queryset = ArticleSet.objects.all()
    permission_map = {'POST': ROLE_PROJECT_ADMIN}

    def filter_queryset(self, queryset):
        queryset = super(ArticleSetViewSet, self).filter_queryset(queryset)
        return queryset.filter(id__in=self.project.all_articlesets())

    def create(self, request, *args, **kwargs):
        if "articleset" in request.data:
            # We're adding an existing set, no need to create a new set
            setids = request.data['articleset']
            if isinstance(setids, int):
                setids = [setids]
            sets = [ArticleSet.objects.get(pk=s) for s in setids]
            self.project.articlesets.add(*sets)
            self.project.favourite_articlesets.add(*sets)
            return Response({"articlesets": setids}, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)



class FavouriteArticleSetViewSetMixin(AmCATViewSetMixin):
    model_key = "favourite_articleset"
    search_fields = ordering_fields = ("id", "name", "provenance")
    model = ArticleSet
    queryset = ArticleSet.objects.all()

class FavouriteArticleSetViewSet(ProjectViewSetMixin, FavouriteArticleSetViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    serializer_class = ArticleSetSerializer
    model_key = "favourite_articleset"
    queryset = ArticleSet.objects.all()

    def filter_queryset(self, queryset):
        queryset = super(FavouriteArticleSetViewSet, self).filter_queryset(queryset)
        return queryset.filter(id__in=self.project.favourite_articlesets.all())

class CodingjobArticleSetViewSetMixin(AmCATViewSetMixin):
    model_key = "codingjob_articleset"
    search_fields = ordering_fields = ("id", "name", "provenance")
    model = ArticleSet


class CodingjobArticleSetViewSet(ProjectViewSetMixin, CodingjobArticleSetViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    serializer_class = ArticleSetSerializer
    model_key = "codingjob_articleset"
    queryset = ArticleSet.objects.all()

    def filter_queryset(self, queryset):
        queryset = super(CodingjobArticleSetViewSet, self).filter_queryset(queryset)
        return queryset.filter(id__in=self.project.all_articlesets(), codingjob_set__id__isnull=False)
