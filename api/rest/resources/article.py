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

from amcat.models import Article, ArticleSet
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer
from api.rest.filters import AmCATFilterSet, InFilter

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

from rest_framework import viewsets

from api.rest.resources.amcatresource import DatatablesMixin

from rest_framework import permissions
from amcat.models.authorisation import ROLE_PROJECT_READER, ROLE_PROJECT_WRITER, ROLE_PROJECT_ADMIN

_PERM_MAP = {
    'OPTIONS' : None,
    'HEAD' : None,
    'GET' : ROLE_PROJECT_READER,
    'POST' : ROLE_PROJECT_WRITER,
    'DELETE' : ROLE_PROJECT_ADMIN
    }

class ProjectPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user if request.user.is_authenticated() else None
        required_role_id = _PERM_MAP[request.method]
        if not required_role_id: return True
        actual_role_id = view.get_project().get_role_id(user=user)
        if not actual_role_id >= required_role_id:
            log.warn("User {user} has role {actual_role_id} < {required_role_id}".format(**locals()))
        return actual_role_id >= required_role_id
    
class ArticleViewSet(DatatablesMixin, viewsets.ModelViewSet):
    permission_classes = (ProjectPermission,)
    model = Article

    @property
    def articleset(self):
        if not hasattr(self, '_articleset'):
            articleset_id = int(self.kwargs['articleset'])
            self._articleset = ArticleSet.objects.get(pk=articleset_id)
        return self._articleset

    def get_project(self):
        return self.articleset.project
    
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

    def test_create(self):
        s = amcattest.create_test_set()
                            
        # is the set empty? (aka can we get the results)
        url = '/api/v4/articleset/{s.id}/articles/'.format(**locals())
        result = self.get(url)
        self.assertEqual(result['results'], [])

        body = {'text' : 'bla', 'headline' : 'headline', 'date' : '2013-01-01T00:00:00',
                'medium' : amcattest.create_test_medium().id,
                'project' : s.project.id,
                'metastring' : '{}',
                'length' : 123}
        result = self.post(url, body, as_user=s.project.owner)
        self.assertEqual(result['headline'], body['headline'])

        
        url = '/api/v4/articleset/{s.id}/articles/'.format(**locals())
        result = self.get(url)
        self.assertEqual(len(result['results']), 1)
