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

class _NoProjectRequestedError(ValueError): pass

class ArticleSetSerializer(AmCATModelSerializer):
    index_status = serializers.SerializerMethodField('get_status')
    favourite = serializers.SerializerMethodField("is_favourite")

    def get_status(self, aset):
        return aset.index_state

    @property
    @cached
    def favourite_articlesets(self):
        """
        List of id's of all favourited projects for the project specified
        by the project_for_favourites GET argument
        (I'm all for a more elegant solution!)
        """

        try:
            project = self.context['request'].GET['project_for_favourites']
        except KeyError:
            raise _NoProjectRequestedError()

        return set(ArticleSet.objects.filter(favourite_of_projects=project).values_list("id", flat=True))

    def is_favourite(self, project):
        try:
            return project.id in self.favourite_articlesets
        except _NoProjectRequestedError:
            return None
    
    class Meta:
        model = ArticleSet

class ArticleSetResource(AmCATResource):
    model = ArticleSet
    serializer_class = ArticleSetSerializer

