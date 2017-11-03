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
from rest_framework.permissions import IsAdminUser

from amcat.models import User

from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer


class UserResource(AmCATResource):
    model = User
    queryset = User.objects.all()

    class serializer_class(AmCATModelSerializer):
        class Meta:
            model = User
            fields = ("id", "username")

    @classmethod
    def get_label(cls):
        return "{username}"
