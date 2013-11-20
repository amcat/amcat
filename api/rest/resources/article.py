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

import json
from django.core.exceptions import ValidationError
from amcat.models import Article, ArticleSet, Medium
from api.rest.resources.amcatresource import AmCATResource
from api.rest.resources.articleset import ArticleSetViewSet

from api.rest.serializer import AmCATModelSerializer
from api.rest.filters import AmCATFilterSet, InFilter
from rest_framework.viewsets import ModelViewSet
from api.rest.resources.amcatresource import DatatablesMixin

from api.rest.viewsets import (ProjectViewSetMixin, ROLE_PROJECT_READER,
                               CannotEditLinkedResource, NotFoundInProject,
                               ProjectSerializer)

from rest_framework import serializers
from django_filters import filters, filterset
import logging
log = logging.getLogger(__name__)

class ArticleMetaFilter(AmCATFilterSet):
    date_from = filters.DateFilter(name='date', lookup_type='gte')
    date_to = filters.DateFilter(name='date', lookup_type='lt')
    articleset = InFilter(name='articlesets_set', queryset=ArticleSet.objects.all())
    
    class Meta:
        model = Article
        order_by=True
        
class ArticleMetaSerializer(AmCATModelSerializer):
    class Meta:
        model = Article
        fields = ("id", "date", "project", "medium", "headline",
                    "section", "pagenr", "author", "length")

class ArticleMetaResource(AmCATResource):
    model = Article
    serializer_class = ArticleMetaSerializer
    filter_class = ArticleMetaFilter
    
    @classmethod
    def get_model_name(cls):
        return "ArticleMeta".lower()

class ArticleSerializer(ProjectSerializer):

    def __init__(self, instance=None, data=None, files=None, **kwargs):
        kwargs['many'] = isinstance(data, list)
        super(ArticleSerializer, self).__init__(instance, data, files, **kwargs)
    
    def restore_fields(self, data, files):
        # convert media from name to id, if needed
        data = data.copy() # make data mutable
        if 'medium' in data:
            try:
                int(data['medium'])
            except ValueError:
                if not hasattr(self, 'media'):
                    self.media = {}
                m = data['medium']
                if m not in self.media:
                    self.media[m] = Medium.get_or_create(m).id
                data['medium'] = self.media[m]
                
        # add time part to date, if needed
        if 'date' in data and len(data['date']) == 10:
            data['date'] += "T00:00"
        
        return super(ArticleSerializer, self).restore_fields(data, files)

    def from_native(self, data, files):
        result = super(ArticleSerializer, self).from_native(data, files)

        # deserialize children (if needed)
        children = data.get('children')# TODO: children can be a multi-value GET param as well, e.g. handle getlist

        if isinstance(children, (str, unicode)):
            children = json.loads(children)
        
        if children:
            self.many = True            
            def get_child(obj):
                child = self.from_native(obj, None)
                child.parent = result
                return child
            return [result] + [get_child(child) for child in children]

        return result
                
    def save(self, **kwargs):
        import collections
        def _flatten(l):
            """Turn either an object or a (recursive/irregular/jagged) list-of-lists into a flat list"""
            # inspired by http://stackoverflow.com/questions/2158395/flatten-an-irregular-list-of-lists-in-python
            if isinstance(l, collections.Iterable) and not isinstance(l, basestring):
                for el in l:
                    for sub in _flatten(el):
                        yield sub
            else:
                yield l
                
        # flatten articles list (children in a many call yields a list of lists)
        self.object = list(_flatten(self.object))

        Article.create_articles(self.object, self.context['view'].articleset)

        # make sure that self.many is True for serializing result
        self.many = True
        return self.object
        
class ArticleViewSet(ProjectViewSetMixin, DatatablesMixin, ModelViewSet):
    model = Article
    url = ArticleSetViewSet.url + '/(?P<articleset>[0-9]+)/articles'
    permission_map = {'GET' : ROLE_PROJECT_READER}
    model_serializer_class = ArticleSerializer
    
    def check_permissions(self, request):
        # make sure that the requested set is available in the projec, raise 404 otherwiset
        # sets linked_set to indicate whether the current set is owned by the project
        if self.articleset.project == self.project:
            pass
        elif self.project.articlesets.filter(pk=self.articleset.id).exists():
            if request.method == 'POST':
                raise CannotEditLinkedResource()
        else:
            raise NotFoundInProject()
        return super(ArticleViewSet, self).check_permissions(request)
    
    
    @property
    def articleset(self):
        if not hasattr(self, '_articleset'):
            articleset_id = int(self.kwargs['articleset'])
            self._articleset = ArticleSet.objects.get(pk=articleset_id)
        return self._articleset

    def filter_queryset(self, queryset):
        queryset = super(ArticleViewSet, self).filter_queryset(queryset)
        return queryset.filter(articlesets_set=self.articleset)

            
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from api.rest.apitestcase import ApiTestCase
from amcat.tools import amcattest
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

class TestArticle(ApiTestCase):
    authentication_classes = (SessionAuthentication, BasicAuthentication)
    
    
    @amcattest.use_elastic
    def test_create(self):
        s = amcattest.create_test_set()
                            
        # is the set empty? (aka can we get the results)
        url = ArticleViewSet.get_url(project=s.project.id, articleset=s.id)
        result = self.get(url)
        self.assertEqual(result['results'], [])

        body = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00', 'medium' : 'test_medium'}
        
        result = self.post(url, body, as_user=s.project.owner)
        if isinstance(result, list): result, = result
        self.assertEqual(result['headline'], body['headline'])
        
        result = self.get(url)
        self.assertEqual(len(result['results']), 1)
        a = result['results'][0]
        self.assertEqual(a['headline'], body['headline'])
        self.assertEqual(a['project'], s.project_id)
        self.assertEqual(a['length'], 2)

        # Is the result added to the elastic index as well?
        from amcat.tools import amcates
        amcates.ES().flush()
        r = list(amcates.ES().query(filters=dict(sets=s.id), fields=["text", "headline", 'medium']))
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].medium, "test_medium")
        self.assertEqual(r[0].headline, "headline") 

    @amcattest.use_elastic
    def test_multiple(self):
        """Can we create multiple objects?"""
        
        s = amcattest.create_test_set()
        url = ArticleViewSet.get_url(project=s.project.id, articleset=s.id)
        base = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00', 'medium' : 'test_medium'}

        a1 = dict(base, headline='a1')
        a2 = dict(base, headline='a2')
        body = json.dumps([a1, a2])
        self.post(url, body, as_user=s.project.owner, request_options=dict(content_type='application/json'))

        result = self.get(url)
        self.assertEqual({r['headline'] for r in result['results']}, {'a1', 'a2'})

    @amcattest.use_elastic
    def test_parents(self):
        """Test parents via nesting"""

        s = amcattest.create_test_set()
        url = ArticleViewSet.get_url(project=s.project.id, articleset=s.id)
        base = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00', 'medium' : 'test_medium'}

        child1 = dict(base, headline='c1')
        child2 = dict(base, headline='c2')
        parent = dict(base, headline='parent')
        
        body = dict(parent, children = json.dumps([child1, child2]))
        self.post(url, body, as_user=s.project.owner)

        # result should have 3 articles, with c1 and c2 .parent set to parent
        result = {a['headline'] : a for a in self.get(url)['results']}
        self.assertEqual(len(result), 3)
        self.assertEqual(result['c1']['parent'], result['parent']['id'])
        self.assertEqual(result['c2']['parent'], result['parent']['id'])
        self.assertEqual(result['parent']['parent'], None)
        
    @amcattest.use_elastic
    def test_parents_multiple(self):
        """Can we add multiple objects with children?"""
        s = amcattest.create_test_set()
        url = ArticleViewSet.get_url(project=s.project.id, articleset=s.id)
        base = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00', 'medium' : 'test_medium'}
                
        child = dict(base, headline='c')
        parent = dict(base, headline='p')
        leaf = dict(base, headline='l')

        body = json.dumps([leaf, dict(parent, children=[child])])
        self.post(url, body, as_user=s.project.owner, request_options=dict(content_type='application/json'))
        
        result = {a['headline'] : a for a in self.get(url)['results']}
        self.assertEqual(len(result), 3)
        self.assertEqual(result['c']['parent'], result['p']['id'])
        self.assertEqual(result['p']['parent'], None)
        self.assertEqual(result['l']['parent'], None)
        
        
    def test_permissions(self):
        from amcat.models import Role, ProjectRole
        metareader = Role.objects.get(label='metareader', projectlevel=True)
        reader = Role.objects.get(label='reader', projectlevel=True)
        
        p1 = amcattest.create_test_project(guest_role=None)
        p2 = amcattest.create_test_project(guest_role=metareader)
        
        s1 = amcattest.create_test_set(project=p1)        
        s2 = amcattest.create_test_set(project=p2)

        p1.articlesets.add(s2)
        #alias
        url, set_url = ArticleViewSet.get_url, ArticleSetViewSet.get_url

        body = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00', 'medium' : 'test_medium'}
        # anonymous user shoud be able to read p2's articlesets but not articles (requires READER), and nothing on p1
                                                  
        self.get(url(project=p1.id, articleset=s1.id), check_status=401)
        self.get(url(project=p2.id, articleset=s2.id), check_status=401)

        self.get(set_url(project=p1.id), check_status=401)
        self.get(set_url(project=p2.id), check_status=200)

        # it is illegal to view an articleset through a project it is not a member of
        self.get(url(project=p2.id, articleset=s1.id), check_status=404)
        
        u = p1.owner
        ProjectRole.objects.create(project=p2, user=u, role=reader)

        # User u shoud be able to view all views
        self.get(url(project=p1.id, articleset=s1.id), as_user=u, check_status=200)
        self.get(url(project=p1.id, articleset=s2.id), as_user=u, check_status=200)
        self.get(url(project=p2.id, articleset=s2.id), as_user=u, check_status=200)
        # Except this one, of course, because it doesn't exist
        self.get(url(project=p2.id, articleset=s1.id), as_user=u, check_status=404)

        self.get(set_url(project=p1.id), as_user=u, check_status=200)
        self.get(set_url(project=p2.id), as_user=u, check_status=200)

        # User u should be able to add articles to set 1 via project 1, but not p2/s2
        self.post(url(project=p1.id, articleset=s1.id), body, as_user=u, check_status=201)
        self.post(url(project=p2.id, articleset=s2.id), body, as_user=u, check_status=403)
        
        # Neither u (p1.owner) nor p2.owner should be able to modify set 2 via project 1
        self.post(url(project=p1.id, articleset=s2.id), body, as_user=u, check_status=403)
        self.post(url(project=p1.id, articleset=s2.id), body, as_user=p2.owner, check_status=403)
