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
from django.db.models import Count
from django_boolean_sum import BooleanSum

from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATPaginationSerializer
from amcat.models import AnalysedArticle
from api.rest.viewsets.analysed_article import AnalysedArticleSerializer


class AnalysedArticlesPaginationSerializer(AmCATPaginationSerializer):
    class Meta:
        object_serializer_class = AnalysedArticleSerializer

class AnalysedArticleResource(AmCATResource):
    model = AnalysedArticle
    extra_filters = ["article__articlesets_set__id", "article__articlesets_set__project__id"]

    use_distinct = False
    serializer_class = AnalysedArticleSerializer
    pagination_serializer_class = AnalysedArticlesPaginationSerializer

    def get_queryset(self, *args, **kargs):
        qs = (super(AnalysedArticleResource, self).get_queryset(*args, **kargs)
              .values("article__articlesets_set__project", "plugin_id", "article__articlesets_set")
              .annotate(assigned=Count("id"), done=BooleanSum("done"), error=BooleanSum("error"))
              )
        return qs

