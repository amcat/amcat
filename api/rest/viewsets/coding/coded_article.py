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
from rest_framework.viewsets import ReadOnlyModelViewSet

from amcat.models import Sentence, CodedArticle, Article, ROLE_PROJECT_READER
from amcat.tools.caching import cached
from amcat.tools import sbd
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingjob import CodingJobViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin, ProjectPermission
from api.rest.viewsets.sentence import SentenceSerializer, SentenceViewSetMixin

__all__ = (
    "CodedArticleSerializer", "CodedArticleViewSetMixin", "CodedArticleViewSet",
    "CodedArticleSentenceViewSet")


def article_property(property_name):
    def inner(self, coded_article):
        return self.get_article(coded_article).get_property(property_name, default=None)

    return inner


class CodedArticleSerializer(AmCATModelSerializer):
    title = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    pagenr = serializers.SerializerMethodField()
    length = serializers.SerializerMethodField()
    article_id = serializers.SerializerMethodField()

    get_title = article_property("title")
    get_date = article_property("date")
    get_pagenr = article_property("pagenr")
    get_length = article_property("length")
    get_article_id = article_property("id")

    def _get_coded_articles(self):
        view = self.context["view"]
        return CodedArticle.objects.filter(id__in=view.filter_queryset(view.get_queryset()))

    @cached
    def _get_articles(self):
        aids = self._get_coded_articles().values_list("article__id", flat=True)
        articles = Article.objects.filter(id__in=aids).only("id", "title", "date", "properties")
        return {a.id: a for a in articles}

    def get_article(self, coded_article):
        return self._get_articles().get(coded_article.article_id)

    class Meta:
        model = CodedArticle


class CodedArticleViewSetMixin(AmCATViewSetMixin):
    queryset = CodedArticle.objects.all()
    serializer_class = CodedArticleSerializer
    model_key = "coded_article"
    model = CodedArticle

    class Meta:
        model = CodedArticle


class CodedArticleViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                          CodedArticleViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    serializer_class = CodedArticleSerializer
    queryset = CodedArticle.objects.all()
    model = CodedArticle

    ordering_mapping = {
        "title": "article__title",
        "date": "article__date",
        "article_id": "article__id",
        "status": "status__id"
    }

    ordering_fields = (('id', "article_id")
                       + tuple(ordering_mapping.keys())
                       + tuple(ordering_mapping.values()))

    def filter_queryset(self, queryset):
        qs = super(CodedArticleViewSet, self).filter_queryset(queryset)
        return qs.filter(id__in=self.codingjob.coded_articles.all())


class CodedArticleSentenceViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                                  CodedArticleViewSetMixin, SentenceViewSetMixin,
                                  DatatablesMixin, ReadOnlyModelViewSet):
    permission_classes = (ProjectPermission,)
    permission_map = {'GET': ROLE_PROJECT_READER}
    serializer_class = SentenceSerializer
    queryset = Sentence.objects.all()
    model = Sentence

    def check_permissions(self, request):
        if request.method != 'GET' or request.user != self.codingjob.coder:
            super(CodedArticleSentenceViewSet, self).check_permissions(request)

    def filter_queryset(self, queryset):
        qs = super(CodedArticleSentenceViewSet, self).filter_queryset(queryset)
        article = Article.objects.get(id=self.coded_article.article_id)
        sentences = qs.filter(id__in=sbd.get_or_create_sentences(article))
        return sentences
