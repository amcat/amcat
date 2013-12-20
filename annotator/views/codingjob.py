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

import logging

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from amcat.models import CodingJob, Project

log = logging.getLogger(__name__)

def index(request, project_id, codingjob_id):
    """returns the HTML for the main annotator page"""
    return render(request, "annotator/codingjob.html", {
        'codingjob': CodingJob.objects.get(id=codingjob_id),
        'project': Project.objects.get(id=project_id),
        'coder' : request.user,
    })
    
def save(request, project_id, codingjob_id, article_id):
    pass
    
def redirect(request, codingjob_id):
    cj = CodingJob.objects.get(id=codingjob_id)
    return HttpResponseRedirect(reverse(index, kwargs={
        "codingjob_id" : codingjob_id, "project_id" : cj.project_id
    }))
