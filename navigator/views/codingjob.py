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

"""View for viewing all codingjobs (for a user)"""
from django.shortcuts import render
from api.rest.datatable import Datatable

from api.rest.resources import CodingJobResource

def index(request):
    """Show unfinished jobs"""
    jobs = Datatable(CodingJobResource)
    jobs = jobs.rowlink_reverse("annotator:annotator-codingjob", args=[9999999999])
    jobs = jobs.filter(coder=request.user).hide('coder', 'articleset', 'unitschema', 'articleschema')#.filter(status='unfinished')

    ctx = locals()
    ctx.update({
        'context': request.user,
        'selected': 'unfinished jobs',
    })

    return render(request, 'codingjobs.html', locals())
