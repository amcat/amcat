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

from amcat.tools.caching import cached

from amcat.models import ArticleSet
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer

from rest_framework import serializers

class ArticleSetSerializer(AmCATModelSerializer):
    index_status = serializers.SerializerMethodField('get_status')
    favourite = serializers.SerializerMethodField("is_favourite")

    def get_status(self, aset):
        return aset.index_state

    @property
    @cached
    def favourite_articlesets(self):
        """List of id's of all favourited projects by the currently logged in user"""
        return set(self.context['request'].user.userprofile
                    .favourite_articlesets.values_list("id", flat=True))

    def is_favourite(self, project):
        return project.id in self.favourite_articlesets
    
    class Meta:
        model = ArticleSet

class ArticleSetResource(AmCATResource):
    model = ArticleSet
    serializer_class = ArticleSetSerializer

