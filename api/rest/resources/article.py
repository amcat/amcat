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

from amcat.models import Article, ArticleSet, Medium
from api.rest.resources.amcatresource import AmCATResource
from api.rest.resources.articleset import ArticleSetViewSet

from api.rest.serializer import AmCATModelSerializer
from api.rest.filters import AmCATFilterSet, InFilter
from rest_framework.viewsets import ModelViewSet
from api.rest.resources.amcatresource import DatatablesMixin

from api.rest.viewsets import (ProjectViewSetMixin, ROLE_PROJECT_READER,
                               CannotEditLinkedResource, NotFoundInProject)

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

class ArticleViewSet(ProjectViewSetMixin, DatatablesMixin, ModelViewSet):
    model = Article
    url = ArticleSetViewSet.url + '/(?P<articleset>[0-9]+)/articles'
    permission_map = {'GET' : ROLE_PROJECT_READER}

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

    def post_save(self, article, created):
        # add to articleset, index
        if created:
            self.articleset.add_articles([article])

    def create(self, request, *args, **kwargs):
        """Lookup medium if needed"""
        # should this be handled by the serializer instead?
        if 'medium' in request.DATA:
            try:
                int(request.DATA['medium'])
            except ValueError:
                mediumid = Medium.get_or_create(request.DATA['medium']).id
                request.DATA['medium'] = mediumid
                
        return super(ArticleViewSet, self).create(request, *args, **kwargs)

            
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from api.rest.apitestcase import ApiTestCase
from amcat.tools import amcattest
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

class TestArticle(ApiTestCase):
    authentication_classes = (SessionAuthentication, BasicAuthentication)

    def test_create(self):
        s = amcattest.create_test_set()
                            
        # is the set empty? (aka can we get the results)
        url = '/api/v4/projects/{s.project.id}/sets/{s.id}/articles/'.format(**locals())
        url = ArticleViewSet.get_url(project=s.project.id, articleset=s.id)
        result = self.get(url)
        self.assertEqual(result['results'], [])

        body = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00', 'medium' : 'test_medium'}
        
        result = self.post(url, body, as_user=s.project.owner)
        self.assertEqual(result['headline'], body['headline'])
        
        result = self.get(url)
        self.assertEqual(len(result['results']), 1)
        a = result['results'][0]
        self.assertEqual(a['headline'], body['headline'])
        self.assertEqual(a['project'], s.project_id)
        self.assertEqual(a['length'], 2)

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
