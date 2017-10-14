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
from django.views.generic.base import RedirectView
from django import http

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

    if not request.user.is_anonymous():
        recent_projects = list(it.islice(((rp, rp.project.get_role_id(user=request.user) >= ROLE_PROJECT_READER)
                                          for rp in RecentProject.get_recent_projects(request.user.userprofile) if rp.project.get_role_id(user=request.user) is not None), MAX_RECENT_PROJECTS))
        
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
        results['project'] = list(Project.objects.filter(name__icontains=search))
        results['articleset'] = list(ArticleSet.objects.filter(name__icontains=search))
        

    def _filter_projects(projects):
        for p in projects:
            role = p.get_role_id(user=request.user)
            if role is not None:
                yield role >= ROLE_PROJECT_READER, p
            
    def _filter_sets(sets):
        for s in sets:
            role = s.project.get_role_id(user=request.user)
            if role is not None:
                yield role >= ROLE_PROJECT_READER, s
    def _filter_articles(arts):
        for a in arts:
            # choose set with best access, lowest project
            sets = [(s.project.get_role_id(user=request.user), -s.project_id, s.id)
                    for s in list(ArticleSet.objects.filter(articles=a.id))]
            (role, negproject, sid) = sorted(sets, reverse=True)[0]
            if role is not None:
                role = role >= ROLE_PROJECT_READER
            yield (role, sid, -negproject, a)

    if results.get('project'): results['project'] = list(_filter_projects(results['project']))
    if results.get('articleset'): results['articleset'] = list(_filter_sets(results['articleset']))
    if results.get('article'): results['article'] = list(_filter_articles(results['article']))
    results = {k: v for (k,v) in results.items() if v}

    # redirect directly if there is only one result on an id search
    if m and len(results) == 1:
        key = list(results.keys())[0]
        val = results[key]
        if len(val) == 1:
            if key == 'project':
                access, obj = val[0]
                return redirect('navigator:articleset-list', obj.id)
            if key == 'articleset':
                access, obj = val[0]
                return redirect('navigator:articleset-details', obj.project_id, obj.id)
            if key == 'article':
                access, sid, pid, obj = val[0]
                return redirect('navigator:article-details', pid, sid, obj.id)

    
    return render(request, 'to_object.html', locals())
    
    
class IndexRedirect(RedirectView):
    permanent = False
    
    def get(self, request, *args, **kwargs):
        if request.user.is_anonymous():
            return http.HttpResponseRedirect("/accounts/login")
        return http.HttpResponseRedirect("/projects")
