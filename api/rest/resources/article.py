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

import logging

from django_filters import filters

from amcat.models import Article, ArticleSet
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer
from api.rest.filters import InFilter, DjangoPrimaryKeyFilterBackend

log = logging.getLogger(__name__)


class ArticleMetaFilter(DjangoPrimaryKeyFilterBackend.default_filter_set):
    date_from = filters.DateFilter(name='date', lookup_expr='gte')
    date_to = filters.DateFilter(name='date', lookup_expr='lt')
    articleset = InFilter(name='articlesets_set', queryset=ArticleSet.objects.all())
    hash = filters.CharFilter(name='hash', lookup_expr='exact')
    parent_hash = filters.CharFilter(name='hash', lookup_expr='exact')

    class Meta:
        model = Article
        exclude = ('properties',)


class ArticleMetaSerializer(AmCATModelSerializer):
    class Meta:
        model = Article
        fields = (
            "id", "date", "project", "title"
        )


class ArticleMetaResource(AmCATResource):
    model = Article
    queryset = Article.objects.all()
    serializer_class = ArticleMetaSerializer
    filter_class = ArticleMetaFilter

    @classmethod
    def get_model_name(cls):
        return "ArticleMeta".lower()

