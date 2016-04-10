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
API Viewsets for status of articleset preprocessing
"""

# TODO WvA: move away from listmodelmixin, doesn't make sense with model=None?

from collections import namedtuple

from nlpipe.backend import count_cached
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.mixins import DatatablesMixin
from rest_framework.viewsets import ModelViewSet, ViewSet, GenericViewSet
from rest_framework import serializers
from rest_framework.mixins import ListModelMixin, CreateModelMixin

ModuleCount = namedtuple("ModuleCount", ["module", "n"])

class PreprocessViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, DatatablesMixin,
                        ListModelMixin, GenericViewSet):
    model_key = "preproces"
    model = None
    base_name = "preprocess"

    class serializer_class(serializers.Serializer):
        module = serializers.CharField()
        n = serializers.IntegerField()
    
    def filter_queryset(self, queryset):
        ids = list(self.articleset.get_article_ids_from_elastic())
        result = [ModuleCount("Total #articles", len(ids))]
        for module, n in count_cached(ids):
            result.append(ModuleCount(module, n))

        return result

    def get_filter_fields(self):
        return []
