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

from amcat.models import Article
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer

from rest_framework import serializers

class ArticleMetaSerializer(AmCATModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "date", "project", "medium")

class ArticleMetaResource(AmCATResource):
    model = Article
    serializer_class = ArticleMetaSerializer

    @classmethod
    def get_model_name(cls):
        return "ArticleMeta".lower()
