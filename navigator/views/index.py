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
import re

from django.shortcuts import render
from amcat.models import ArticleSet, RecentProject, Project, Article
from amcat.models.authorisation import ROLE_PROJECT_READER

from django.shortcuts import redirect

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

    recent_projects = list(it.islice(((rp, rp.project.get_role_id(user=request.user) >= ROLE_PROJECT_READER)
                     for rp in RecentProject.get_recent_projects(request.user.userprofile)), MAX_RECENT_PROJECTS))

    return render(request, 'index.html', locals())

def to_object(request):
    def _get(cls, id):
        try:
            return cls.objects.get(pk=id)
        except cls.DoesNotExist:
            pass
    search = request.GET.get('search')

    if not search:
        return render(request, 'to_object.html', locals())

    results = {}
    
    m = re.match("([psa]?)(\d+)", search)
    if m:
        query = "id {search}".format(**locals())
        what, id = m.groups()
        p = _get(Project, id) if (not what) or what == "p" else None
        s = _get(ArticleSet, id) if (not what) or what == "s" else None
        a = _get(Article, id) if (not what) or what == "a" else None
        
        for x in (p,s,a):
            if x:
                cls = x.__class__.__name__.lower()
                results[cls] = [x]
    else:
        query = search
        projects = Project.objects.filter(name__icontains=search)
        if projects:
            results['project'] = projects
        sets = ArticleSet.objects.filter(name__icontains=search)
        if sets:
            results['articleset'] = sets
        
        
    
    if len(results) == 1 and len(results.values()[0]) == 1:
        (key, (val,)), = results.items()
        if key == 'project':
            return redirect('navigator:articleset-list', val.id)
        if key == 'articleset':
            return redirect('navigator:articleset-details', val.project_id, val.id)
        if key == 'article':
            s = ArticleSet.objects.filter(articles=val.id)[0]
            return redirect('navigator:article-details', s.project_id, s.id, val.id)

    
    return render(request, 'to_object.html', locals())
    
    
