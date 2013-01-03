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
from django.shortcuts import render
from navigator.utils.auth import check

from amcat.models.coding.codingschema import CodingSchema
from api.rest.resources import CodingSchemaResource

from api.rest.datatable import Datatable

import logging; log = logging.getLogger(__name__)

def index(request):
    all_schemas = Datatable(CodingSchemaResource, options=dict(iDisplayLength=10))
    own_schemas = all_schemas.filter(project__in=request.user.projects)

    return render(request, 'navigator/schemas/index.html', locals())

@check(CodingSchema)
def schema(request, aschema):
    return render(request, 'navigator/schemas/schema.html', locals())
