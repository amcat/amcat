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

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ReadOnlyModelViewSet

from amcat.models import Sentence, CodedArticle, Article, ROLE_PROJECT_READER, CodingJob, Project
from amcat.tools.amcates import get_property_primitive_type
from amcat.tools.caching import cached
from amcat.tools import sbd
from api.rest.metadata import AmCATMetadata
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingjob import CodingJobViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin, ProjectPermission
from api.rest.viewsets.sentence import SentenceSerializer, SentenceViewSetMixin

__all__ = (
    "CodedArticleSerializer", "CodedArticleViewSetMixin", "CodedArticleViewSet",
    "CodedArticleSentenceViewSet")

TYPE_FIELDS = {
    str: serializers.CharField,
    int: serializers.IntegerField,
    float: serializers.FloatField,
    datetime.datetime: serializers.DateTimeField
}

def article_property(property_name):
    def inner(self, coded_article):
        return self.get_article(coded_article).get_property(property_name, default=None)
    return inner


def get_property_field_cls(property):
    type = get_property_primitive_type(property)
    base_field = TYPE_FIELDS[type]

    class PropertyField(base_field):
        def get_attribute(self, instance):
            return instance.article.properties.get(property)

    return PropertyField

class CodedArticleSerializer(AmCATModelSerializer):
    article_id = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    get_title = article_property("title")
    get_date = article_property("date")
    get_article_id = article_property("id")

    def _split_property_name(self, prop):
        try:
            name, dt = prop.split("_")
            return name, dt
        except ValueError:
            return prop, "default"

    @cached
    def _get_display_properties(self):
        props = set()
        try:
            view = self.context["view"]
            proj = Project.objects.get(pk=view.kwargs["project"])
            codingjob = CodingJob.objects.get(pk=view.kwargs["codingjob"])
            for prop in [x for x in proj.get_display_columns() if x in codingjob.articleset.get_used_properties()]:
                props.add(prop)
        except KeyError:
            pass
        return props


    def _get_properties(self):
        for prop in self._get_display_properties():
            name, _ = self._split_property_name(prop)
            yield name, get_property_field_cls(prop)()

    def get_fields(self):
        fields = super().get_fields()
        try:
            fields.update(self._get_properties())
        except KeyError:
            pass

        # hide these two fields in the annotator. Nobody really needs them anywhere else anyway.
        fields.pop("codingjob", None)
        fields.pop("article", None)

        return fields

    def _get_coded_articles(self):
        view = self.context["view"]
        ids = [ca.id for ca in view.paginate_queryset(view.filter_queryset(view.get_queryset()))]
        return CodedArticle.objects.filter(id__in=ids)

    @cached
    def _get_articles(self):
        aids = self._get_coded_articles().values_list("article__id", flat=True)
        articles = Article.objects.filter(id__in=aids).only("id", "title", "date", "properties")
        return {a.id: a for a in articles}

    def get_article(self, coded_article):
        return self._get_articles().get(coded_article.article_id)

    class Meta:
        model = CodedArticle
        fields = '__all__'


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
