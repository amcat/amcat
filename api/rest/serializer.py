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

from amcat.models import Project
import logging

from amcat.tools.caching import cached


class AmCATModelSerializer(serializers.ModelSerializer):
    def get_fields(self):
        fields = super(AmCATModelSerializer, self).get_fields()

        return collections.OrderedDict(
            [(name, field) for (name, field) in fields.items()
              if not isinstance(field, ManyRelatedField)]
        )


class AmCATProjectModelSerializer(AmCATModelSerializer):
    
    @property
    def project_id(self):
        project_id = self.context["view"].kwargs.get('project')
        if not project_id:
            logging.warn("Could not find project in kwargs: {}".format(self.context["view"].kwargs))
        return project_id

    @property
    def project(self):
        if self.project_id is None:
            return None
        if getattr(self, '_project', None) is None:
            self._project = Project.objects.get(pk=self.project_id)
        return self._project

    def to_internal_value(self, data):
        if 'project' not in data:
            data = dict(data.items())
            data['project'] = self.project_id
        value = super(AmCATProjectModelSerializer, self).to_internal_value(data)
        return value
