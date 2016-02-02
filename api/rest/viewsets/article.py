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
from django.forms import ModelChoiceField

from rest_framework.fields import ModelField, CharField
from rest_framework.viewsets import ModelViewSet

from amcat.models import Medium, Project
from amcat.tools.amcates import ES
from amcat.tools.caching import cached
from api.rest.filters import MappingOrderingFilter
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATProjectModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from amcat.models import Article, ArticleSet, ROLE_PROJECT_READER
from api.rest.viewsets.project import CannotEditLinkedResource, NotFoundInProject
from django.db.models.query_utils import DeferredAttribute

__all__ = ("ArticleSerializer", "ArticleViewSet")
import logging
log = logging.getLogger(__name__)

class ArticleViewSetMixin(AmCATViewSetMixin):
    queryset = Article.objects.all()
    model_key = "article"
    model = Article

class MediumField(ModelField):

    def __init__(self, model_field, representation="name", *args, **kargs):
        super(MediumField, self).__init__(model_field, *args, **kargs)
        self.representation = representation
        self._cache = {} # should be safe as field is initiated per request
    
    def to_internal_value(self, data):
        try:
            int(data)
        except ValueError:
            return Medium.get_or_create(data)
        else:
            return super(MediumField, self).to_internal_value(data)

    def to_representation(self, obj):
        if self.representation == "name":
            if obj.medium_id in self._cache:
                return self._cache[obj.medium_id]
            else:
                self._cache[obj.medium_id] = obj.medium.name
                return obj.medium.name
        return obj.medium_id

from rest_framework import serializers
class ArticleListSerializer(serializers.ListSerializer):
    
    def to_representation(self, data):
        # check if text attribute is defferred
        if data and isinstance(data[0].__class__.__dict__.get('text'), DeferredAttribute):
            # text is deferred, so let's requery this whole page
            ids = [d.id for d in data]
            data = Article.objects.filter(pk__in=ids).prefetch_related("medium")
            
        result = super(ArticleListSerializer, self).to_representation(data)
        return result
    
class ArticleSerializer(AmCATProjectModelSerializer):
    project = ModelChoiceField(queryset=Project.objects.all(), required=True)
    medium = MediumField(model_field=ModelChoiceField(queryset=Medium.objects.all()))
    mediumid = MediumField(model_field=ModelChoiceField(queryset=Medium.objects.all()), representation="id", required=False)
    uuid = CharField(read_only=False, required=False)

    def create(self, validated_data):
        art = Article(**validated_data)
        articleset = self.context["view"].kwargs.get('articleset')
        if articleset: articleset = ArticleSet.objects.get(pk=articleset)
        Article.create_articles([art], articleset=articleset)
        return art

    class Meta:
        model = Article
        read_only_fields = ('id', 'length', 'insertdate', 'insertscript')
        list_serializer_class = ArticleListSerializer

        
class SmartParentFilter(MappingOrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = super(SmartParentFilter, self).get_ordering(request, queryset, view)
        if ordering and "parent" in ordering:
            ordering.remove("parent")
        return ordering

    def order_parent(self, request, queryset, view):
        ordering = super(SmartParentFilter, self).get_ordering(request, queryset, view)
        return ordering and  "parent" in ordering

    
    def filter_queryset(self, request, queryset, view):
        result = super(SmartParentFilter, self).filter_queryset(request, queryset, view)

        if self.order_parent(request, queryset, view):
            result = list(result.only("id", "parent"))
            result = list(parents_first_order(result))
        
        return result

def parents_first_order(articles):
    "Reorder articles such that parent comes before children (if parent is present)"
    all_ids = {a.id for a in articles}
    seen = set()
    todo = articles
    while todo:
        new_todo = []
        for a in todo:
            if a.parent_id and a.parent_id in all_ids and a.parent_id not in seen:
                new_todo.append(a)
            else:
                seen.add(a.id)
                yield a
        if len(new_todo) >= len(todo):
            raise ValueError("Cyclical parent ordering!")
        todo = new_todo


            

        
class ArticleViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, ArticleViewSetMixin, DatatablesMixin, ModelViewSet):
    model = Article
    model_key = "article"
    permission_map = {'GET': ROLE_PROJECT_READER}
    serializer_class = ArticleSerializer
    queryset = Article.objects.all()
    http_method_names = ("get", "post")
    ordering_fields = ("id", "parent")
    filter_backends = (SmartParentFilter,)

    def check_permissions(self, request):
        # make sure that the requested set is available in the projec, raise 404 otherwiset
        # sets linked_set to indicate whether the current set is owned by the project
        if self.articleset.project == self.project:
            pass
        elif self.project.articlesets.filter(pk=self.articleset.id).exists():
            if request.method == 'POST':
                raise CannotEditLinkedResource()
        else:
            raise NotFoundInProject()
        return super(ArticleViewSet, self).check_permissions(request)

    @property
    @cached
    def articleset(self):
        articleset_id = int(self.kwargs['articleset'])
        return ArticleSet.objects.get(pk=articleset_id)

    def filter_queryset(self, queryset):
        queryset = queryset.filter(articlesets_set=self.articleset)
        queryset = super(ArticleViewSet, self).filter_queryset(queryset)
        return queryset
