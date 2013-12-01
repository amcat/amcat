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

from annotator.views.codingjob import redirect
from api.rest.resources import CodingJobResource
from api.rest.datatable import Datatable


def index(request):
    table = (Datatable(CodingJobResource).filter(coder__id=request.user.id)
             .rowlink_reverse(redirect, args=["{id}"])
             .hide("unitschema", "articleschema", "insertuser", "coder", "articleset")
             .order_by("insertdate"))
    return render(request, "annotator/overview.html", locals())
    
    
