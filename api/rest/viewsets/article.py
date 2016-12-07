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

"""
Article API end-point at projects/pid/articlesets/sid/articles[/aid]

This end-point accepts the 'normal' model viewsets, i.e.
GET articles gives a list of articles
GET articles/aid gives a single article
POST articles < dict can post a single article

However, it also supports addition POST options:
POST articles < list-of-dicts can post multiple articles
POST articles < aid OR {"id": aid}] can add an existing article to a set
POST articles < [aid, ] OR [{"id": aid}, ] can add multiple existing article to a set

GET requests return the full metadata of the article, not including text (use articles/123/text)
POST requests return only the ids of the created articles
"""

# WvA: this is a merger of the article-pload and articles end points, and contains some redundancy
#     but I think we should clean it up once we deal with parents (issue #460)

import logging
import re

from django.forms import ModelChoiceField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from amcat.models import Article, ArticleSet, ROLE_PROJECT_READER
from amcat.models import Project, PropertyMapping
from amcat.models.article import _check_read_access
from amcat.tools.caching import cached
from api.rest.filters import MappingOrderingFilter
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATProjectModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import CannotEditLinkedResource, NotFoundInProject
from api.rest.viewsets.project import ProjectViewSetMixin

re_uuid = re.compile("[0-F]{8}-[0-F]{4}-[0-F]{4}-[0-F]{4}-[0-F]{12}", re.I)
log = logging.getLogger(__name__)

__all__ = ("ArticleSerializer", "ArticleViewSet")


def is_uuid(val):
    return isinstance(val, str) and re_uuid.match(val)


class ArticleViewSetMixin(AmCATViewSetMixin):
    queryset = Article.objects.all()
    model_key = "article"
    model = Article


class ArticleListSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise ValidationError("Article upload content should be a list of dicts!")

        def _process_ids(article):
            if isinstance(article, int):
                article = {"id": article}
            return article

        data = [_process_ids(a) for a in data]

        return super(ArticleListSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        def _process_children(article_dicts, parent=None):
            for adict in article_dicts:
                children = adict.pop("children")
                if parent is not None:
                    assert 'parent_hash' not in adict
                    adict['parent_hash'] = parent.compute_hash()
                article = Article(**adict)
                yield article
                yield from _process_children(children, parent=article)

        articleset = self.context["view"].kwargs.get('articleset')
        if articleset:
            articleset = ArticleSet.objects.get(pk=articleset)

        to_add = [a['id'] for a in validated_data if "id" in a]
        to_create = [a for a in validated_data if "id" not in a]
        if to_create:
            articles = list(_process_children(to_create))
            yield from Article.create_articles(articles, articleset=articleset)
        if to_add:
            _check_read_access(self.context['request'].user, to_add)
            articleset.add_articles(to_add)
            yield from Article.objects.filter(pk__in=to_add).only("pk")

    def to_representation(self, data):
        # check if text attribute is defferred  - is this still needed?
        if u'RelatedManager' in str(type(data)):
            data = list(data.all())
        result = super(ArticleListSerializer, self).to_representation(data)
        for r in result:
            if r.get('parent'):
                r['parent'] = unicode(uuids[r['parent']])
        return result


class ArticleSerializer(AmCATProjectModelSerializer):
    project = ModelChoiceField(queryset=Project.objects.all(), required=True)

    def to_internal_value(self, data):
        if isinstance(data, int):
            return {"id": data}
        if 'id' in data:
            if set(data.keys()) != {"id"}:
                raise ValidationError(
                    "When uploading explicit ID, specifying other fields is not allowed")
            return {"id": int(data['id'])}
        if 'properties' not in data:
            data['properties'] = PropertyMapping()
        if 'children' not in data:
            data['children'] = []
        ARTICLE_FIELDS = set(super(ArticleSerializer, self).get_fields().keys())
        # add all other fields to properties
        for field in data.keys() - (ARTICLE_FIELDS | {"children"}):
            data['properties'][field] = data.pop(field)
        return super(ArticleSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        articleset = self.context["view"].kwargs.get('articleset')
        if articleset: articleset = ArticleSet.objects.get(pk=articleset)

        if 'id' in validated_data:
            _check_read_access(self.context['request'].user, [validated_data['id']])
            art = Article.objects.get(pk=validated_data['id'])
            if articleset:
                articleset.add_articles([art])

        else:
            validated_data.pop('children')
            art = Article(**validated_data)
            Article.create_articles([art], articleset=articleset)
        return art

    def get_fields(self):
        fields = super(ArticleSerializer, self).get_fields()
        if self.context['request'].method == "POST":
            fields["children"] = ArticleSerializer(many=True)
        elif not self.context['view'].text:
            del fields["text"]
        return fields

    def to_representation(self, data):
        if self.context['request'].method == "POST":
            return {"id": data.id}
        result = super(ArticleSerializer, self).to_representation(data)
        result.update(result.pop('properties'))
        return result

    class Meta:
        model = Article
        read_only_fields = ('id', 'insertdate', 'insertscript')
        list_serializer_class = ArticleListSerializer


class SmartParentFilter(MappingOrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = super(SmartParentFilter, self).get_ordering(request, queryset, view)
        if ordering and "parent" in ordering:
            ordering.remove("parent")
        return ordering

    def order_parent(self, request, queryset, view):
        ordering = super(SmartParentFilter, self).get_ordering(request, queryset, view)
        return ordering and "parent" in ordering

    def filter_queryset(self, request, queryset, view):
        result = super(SmartParentFilter, self).filter_queryset(request, queryset, view)

        if self.order_parent(request, queryset, view):
            result = list(result.only("id", "parent"))
            result = list(parents_first_order(result))

        return result


def parents_first_order(articles):
    """Reorder articles such that parent comes before children (if parent is present)"""
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


class ArticleViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, ArticleViewSetMixin,
                     DatatablesMixin, ModelViewSet):
    model = Article
    model_key = "article"
    serializer_class = ArticleSerializer
    queryset = Article.objects.all()
    http_method_names = ("get", "post")
    ordering_fields = ("id", "parent")
    filter_backends = (SmartParentFilter,)

    def check_permissions(self, request):
        # make sure that the requested set is available in the projec, raise 404 otherwiset
        # sets linked_set to indicate whether the current set is owned by the project
        if self.articleset.project_id == self.project.id:
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

    @property
    def text(self):
        text = self.request.GET.get('text', 'n').upper()
        return text and (text[0] in ('Y', 'T', '1'))

    def required_role_id(self, request):
        if request.method == "GET" and self.text:
            return ROLE_PROJECT_READER
        return super(ArticleViewSet, self).required_role_id(request)

    def filter_queryset(self, queryset):

        queryset = queryset.filter(articlesets_set=self.articleset)
        queryset = super(ArticleViewSet, self).filter_queryset(queryset)
        if not self.text:
            queryset = queryset.defer("text")

        return queryset

    def get_serializer(self, *args, **kwargs):
        if ('many' not in kwargs) and ('data' in kwargs):
            kwargs['many'] = isinstance(kwargs['data'], list)
        return super(ArticleViewSet, self).get_serializer(*args, **kwargs)
