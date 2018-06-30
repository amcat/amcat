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
POST articles < aid OR {"id": aid} can add an existing article to a set
POST articles < [aid, ] OR [{"id": aid}, ] can add multiple existing article to a set

GET requests return the full metadata of the article, not including text (use articles/123/text)
POST requests return only the ids of the created articles
"""

# WvA: this is a merger of the article-pload and articles end points, and contains some redundancy
#     but I think we should clean it up once we deal with parents (issue #460)
import datetime
import logging
import re
from typing import List, Dict, Any, Union

from django.forms import ModelChoiceField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
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


def json_to_article(article: Dict[str, Any], project: Project) -> Article:
    article = Article(project=project, **article)
    article.compute_hash()
    return article


def article_to_json(article: Article) -> Dict[str, Union[str, int, float, datetime.datetime]]:
    return {
        "title": article.title,
        "text": article.text,
        "hash": article.hash,
        "parent_hash": article.parent_hash,
        "url": article.url,
        "date": article.date,
        "properties": dict(article.get_properties())
    }


class ArticleViewSetMixin(AmCATViewSetMixin):
    queryset = Article.objects.all()
    model_key = "article"
    model = Article


class ArticleListSerializer(serializers.ListSerializer):
    """Defines methods to """
    def to_internal_value(self, articles: List[Dict[Any, Any]]):
        # Must be supplied a list, or error:
        if not isinstance(articles, list):
            message = self.error_messages['not_a_list'].format(input_type=type(articles).__name__)
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: [message]})

        if not articles:
            return []

        # If a user supplied a list of ints, we assume a list of article ids
        if isinstance(articles[0], int):
            articles = [{"id": id} for id in articles]

        return super(ArticleListSerializer, self).to_internal_value(articles)

    def create(self, validated_data):
        # Get articleset object given through URL
        articleset_id = self.context["view"].kwargs.get('articleset')
        if articleset_id is not None:
            articleset = ArticleSet.objects.get(pk=articleset_id)
            project = articleset.project
        else:
            raise ValueError("Missing articleset parameter?")

        # Create articles not yet in database
        new_articles = [a for a in validated_data if "id" not in a]
        if new_articles:
            new_articles = [json_to_article(article, project) for article in new_articles]
            yield from Article.create_articles(new_articles, articleset=articleset)

        # Add existing articles to this set
        to_add = [a['id'] for a in validated_data if "id" in a]
        if to_add:
            _check_read_access(self.context['request'].user, to_add)
            articleset.add_articles(to_add)
            yield from Article.objects.filter(pk__in=to_add).only("pk")


class ArticleSerializer(AmCATProjectModelSerializer):
    project = ModelChoiceField(queryset=Project.objects.all(), required=True)

    def get_articleset(self):
        articleset_id = self.context["view"].kwargs.get('articleset')
        if articleset_id is not None:
            return ArticleSet.objects.get(pk=articleset_id)
        raise ValueError("Missing articleset parameter?")

    def to_internal_value(self, data):
        # Get articleset object given through URL
        articleset = self.get_articleset()

        # Check if user supplied single article id
        if isinstance(data, int):
            return {"id": data}

        # Check if user supplied a dictionary with a single id
        if 'id' in data:
            if len(data.keys()) > 1:
                raise ValidationError("When uploading explicit ID, specifying other fields is not allowed")
            return {"id": int(data['id'])}

        # User supplied a new article
        return article_to_json(json_to_article(data, articleset.project))

    def create(self, validated_data):
        articleset = self.get_articleset()

        if 'id' in validated_data:
            _check_read_access(self.context['request'].user, [validated_data['id']])
            article = Article.objects.get(pk=validated_data['id'])
            articleset.add_articles([article])
        else:
            article = json_to_article(validated_data, articleset.project)
            Article.create_articles([article], articleset=articleset)

        return article

    def get_fields(self):
        fields = super(ArticleSerializer, self).get_fields()
        if not self.context['view'].text:
            del fields["text"]
        return fields

    def to_representation(self, data):
        if self.context['request'].method == "POST":
            return {"id": data.id}
        return super(ArticleSerializer, self).to_representation(data)

    class Meta:
        model = Article
        read_only_fields = ('id', 'insertdate', 'insertscript')
        list_serializer_class = ArticleListSerializer
        fields = '__all__'


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
