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
from amcat.models import Coding, Article
from amcat.tools.caching import cached
from api.rest.resources.amcatresource import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewsets import CodingJobViewSetMixin

__all__ = ("CodedArticleSerializer", "CodedArticleViewSetMixin", "CodedArticleViewSet")

_CA_FIELDS = {
    "id", "headline", "date", "medium", "pagenr", "length",
    "status", "comments", "coding", "comments"
}

class CodedArticleSerializer(AmCATModelSerializer):
    model = Article

    comments = serializers.SerializerMethodField('get_comments')
    status = serializers.SerializerMethodField('get_status')

    @property
    def codings(self):
        codings = Coding.objects.filter(codingjob=self.codingjob, sentence=None)
        if hasattr(self.context["view"], "object_list"):
            return codings.filter(article__in=self.context["view"].object_list)
        return codings.filter(article=self.object)

    @cached
    def get_codings(self):
        codings = self.codings.values_list("id", "status__label", "comments")
        return { c[0] : (c[1], c[2]) for c in codings }

    def get_comments(self, article):
        return self.get_codings()[article.id][1] if article.id in self.get_codings() else None

    def get_status(self, article):
        return self.get_codings()[article.id][0] if article.id in self.get_codings() else "Not started"

    def skip_field(cls, name, field):
        return super(CodedArticleSerializer, cls).skip_field(name, field) or (
            name not in _CA_FIELDS
        )

    @property
    def codingjob(self):
        return self.context["view"].codingjob

class CodedArticleViewSetMixin(CodingJobViewSetMixin):
    url = CodingJobViewSetMixin.url + "/(?P<codingjob>[0-9]+)/articles"
    model_serializer_class = CodedArticleSerializer

    @property
    def article(self):
        return self._article()

    @cached
    def _article(self):
        return Article.objects.get(id=self.kwargs.get("article"))

class CodedArticleViewSet(CodedArticleViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Article

    def filter_queryset(self, queryset):
        qs = super(CodedArticleViewSet, self).filter_queryset(queryset)
        return qs.filter(id__in=self.codingjob.articleset.articles.all())

