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

    recent_projects = it.islice(((rp, rp.project.get_role_id(user=request.user) >= ROLE_PROJECT_READER)
                     for rp in RecentProject.get_recent_projects(request.user.userprofile)), 5)

    return render(request, 'index.html', locals())
