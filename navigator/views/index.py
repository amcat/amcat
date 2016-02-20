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
import itertools as it

from django.shortcuts import render
from amcat.models import ArticleSet, RecentProject
from amcat.models.authorisation import ROLE_PROJECT_READER
from django.views.generic.base import RedirectView
from django import http

MAX_RECENT_PROJECTS = 5

def index(request):
    try:
        fluid = int(request.GET['fluid'])
    except (ValueError, KeyError):
        pass
    else:
        print(request.user.userprofile.fluid)
        request.user.userprofile.fluid = fluid > 0
        request.user.userprofile.save()
        print(request.user.userprofile.fluid)
    
    featured_sets = [(aset, aset.project.get_role_id(user=request.user) >= ROLE_PROJECT_READER)
                     for aset in ArticleSet.objects.filter(featured=True)]

    if not request.user.is_anonymous():
        recent_projects = list(it.islice(((rp, rp.project.get_role_id(user=request.user) >= ROLE_PROJECT_READER)
                                          for rp in RecentProject.get_recent_projects(request.user.userprofile)), MAX_RECENT_PROJECTS))
        
    return render(request, 'index.html', locals())

class IndexRedirect(RedirectView):
    permanent = False
    
    def get(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            url = "accounts/login"
        else:
            url = "navigator"
        return http.HttpResponseRedirect(url)
