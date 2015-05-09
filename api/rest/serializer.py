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
AmCAT-specific adaptations to rest_framework serializers
"""
import collections

from rest_framework import serializers
from rest_framework.relations import ManyRelatedField


class AmCATModelSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super(AmCATModelSerializer, self).get_fields()

        return collections.OrderedDict(
            [(name, field) for (name, field) in fields.iteritems()
              if not isinstance(field, ManyRelatedField)]
        )

