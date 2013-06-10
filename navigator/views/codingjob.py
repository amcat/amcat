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

"""View for viewing all coding jobs (for a user)"""

from django.shortcuts import render
from api.rest import Datatable

from navigator.utils.auth import check
from amcat.models.user import User

from settings.menu import CODINGJOB_MENU
from api.rest.resources import CodingJobResource

@check(User, args='coder_id', args_map={'coder_id' : 'id'})
def index(request, coder=None):
    """
    Show unfinished jobs
    """
    coder = coder if coder is not None else request.user

    jobs = Datatable(CodingJobResource, rowlink='/annotator/codingjob/{id}')
    jobs = jobs.filter(coder=coder).hide('coder',)#.filter(status='unfinished')

    ctx = locals()
    ctx.update({
        'menu' : CODINGJOB_MENU,
        'context' : coder,
        'selected' : 'unfinished jobs'
    })

    return render(request, 'navigator/report/codingjobs.html', locals())

@check(User, args='coder_id', args_map={'coder_id' : 'id'})
def all(request, coder):
    """
    Show all (including finished) jobs
    """
    jobs = Datatable(CodingJobResource).filter(coder=coder)

    ctx = locals()
    ctx.update({
        'jobs' : jobs,
        'menu' : CODINGJOB_MENU,
        'context' : coder,
        'selected' : 'all jobs'
    })

    return render(request, 'navigator/report/codingjobs.html', ctx)
