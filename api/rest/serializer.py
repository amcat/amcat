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

"""
AmCAT-specific adaptations to rest_framework serializers
activated by settings.REST_FRAMEWORK['DEFAULT_PAGINATION_SERIALIZER_CLASS']
"""
import collections

from rest_framework import pagination, serializers
from rest_framework.relations import PrimaryKeyRelatedField

from api.rest.fields import DatatablesEchoField

class AmCATPaginationSerializer(pagination.BasePaginationSerializer):
    """
    Rename and add some fields of pagination for datatable js
    """
    echo = DatatablesEchoField(source='*')
    total = serializers.Field(source='paginator.count')
    pages = serializers.Field(source='paginator.num_pages')
    page = serializers.Field(source='number')
    per_page = serializers.Field(source='paginator.per_page')
    next = pagination.NextPageField(source='*')
    previous = pagination.PreviousPageField(source='*')

class AmCATModelSerializer(serializers.ModelSerializer):

    @classmethod
    def skip_field(cls, field):
        """Do we skip serializing this field?"""
        return isinstance(field, PrimaryKeyRelatedField) and field.many
    
    def get_fields(self):
        fields = super(AmCATModelSerializer, self).get_fields()

        return collections.OrderedDict(
            [(name, field) for (name, field) in fields.iteritems()
              if not self.skip_field(field)]
        )


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase

class TestSerializer(ApiTestCase):


    def test_get_object(self):
        from api.rest.resources import ArticleResource
        a = amcattest.create_test_article(
            headline=u'\xba\xa2\u0920\u0903\u0905\u0920\u0940\u1e00\u1e80\u1eb6\u1ef3')
        # (why not test some unicode while we're at it...)
        a2 = self.get_object(ArticleResource, a.id)
        self.assertEqual(a.headline, a2.headline)
        self.assertEqual(a.id, a2.id)

    def test_echo(self):
        from api.rest.resources import ProjectResource

        res = self.get(ProjectResource, datatables_options='{"sEcho":5}')
        self.assertEqual(res['echo'], 5)
    
    def test_get(self):
        from api.rest.resources import ArticleResource, ProjectResource
        from amcat.tools import toolkit
        
        p1 = amcattest.create_test_project(name="testnaam", description="testdescription", insert_date='2012-01-01')

        actual = self.get(ProjectResource, id=p1.id)

        actual_results = actual.pop("results")
        self.assertEqual(len(actual_results), 1)
        actual_results = actual_results[0]
        
        date = actual_results.pop('insert_date')
        toolkit.readDate(date)# check valid date, not much more to check here?

        expected_results={u'insert_user': p1.insert_user.id,
                           u'index_default': True,
                           u'description': 'testdescription',
                           u'name': u'testnaam',
                           u'guest_role': 11,
                           u'owner': p1.owner.id,
                           u'active': True,
                           u'id': p1.id,
                           u'favourite' : False,
                           }
        
        expected_meta = {
            u'page' : 1,
            u'next' : None,
            u'previous' : None,
            u'per_page' : 10,
            u'total' : 1,
            u'pages' : 1,
            u'echo' : None,
            }

        self.assertDictsEqual(actual, expected_meta)
        self.assertDictsEqual(actual_results, expected_results)
