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

from amcat.tools import amcattest
from api.rest.apitestcase import ApiTestCase
from api.rest.resources import ProjectResource
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer
from amcat.models import Project


class TestAmCATResource(ApiTestCase):
    def test_get_field_names(self):

        # Test order of fields.
        class TestSerializer(AmCATModelSerializer):
            class Meta:
                model = Project
                fields = ('name', 'description', 'id')

        class TestResource(AmCATResource):
            model = Project
            serializer_class = TestSerializer

        self.assertEqual(
            tuple(TestResource.get_field_names()),
            ('name', 'description', 'id')
        )

        # Test exclude
        class TestSerializer(AmCATModelSerializer):
            class Meta:
                model = Project
                exclude = ('id',)

        class TestResource(AmCATResource):
            model = Project
            serializer_class = TestSerializer

        self.assertTrue('id' not in TestResource.get_field_names())


    def test_page_size(self):
        from api.rest.resources import ProjectResource

        amcattest.create_test_project(name="t", description="t", insert_date="2011-01-01")
        amcattest.create_test_project(name="t2", description="t2", insert_date="2011-01-01")

        # Assumes that default page_size is greater or equal to 2..
        self.assertEqual(len(self.get(ProjectResource)['results']), 2)

        res = self.get(ProjectResource, page_size=1)
        self.assertEqual(len(res['results']), 1)
        self.assertEqual(res['total'], 2)
        self.assertEqual(res['per_page'], 1)

    def test_options(self):
        opts = self.get_options(ProjectResource)
        name = u'api-v4-project'
        models = {u'owner': u'/api/v4/user', u'guest_role': u'/api/v4/role',
                  #these should NOT be included as we don't want the foreign key fields
                  #u'codebooks': u'/api/v4/codebook',
                  #u'codingschemas': u'/api/v4/codingschema',
                  #u'articlesets': u'/api/v4/articleset',
                  u'insert_user': u'/api/v4/user', }

        fields = {u'name': u'CharField',
                  u'guest_role': u'ModelChoiceField',
                  #these should NOT be included as we don't want the foreign key fields
                  #u'codebooks': u'ModelChoiceField', u'codingschemas': u'ModelChoiceField',
                  #u'articlesets': u'ModelChoiceField',
                  u'owner': u'ModelChoiceField', u'active': u'BooleanField', u'description': u'CharField',
                  u'id': u'IntegerField',
                  u'insert_date': u'DateTimeField',
                  u'insert_user': u'ModelChoiceField',
                  u'last_visited_at': u'SerializerMethodField',
                  u'favourite': u'SerializerMethodField',
                  }
        parses = [u'application/json', u'application/x-www-form-urlencoded', u'multipart/form-data',
                  u'application/xml']
        label = u'{name}'
        renders = {u'application/json', u'text/html'}#, u'text/csv'}
        description = u''


        self.assertEqual(opts['name'], name)
        self.assertEqual(opts['label'], label)
        self.assertEqual(opts['description'], description)



        self.assertDictsEqual(opts['models'], models)
        self.assertDictsEqual(opts['fields'], fields)
        # CSV not supported yet, this will fail:
        missing = renders - set(opts['renders'])
        self.assertFalse(missing, "Missing renderers: {missing}".format(**locals()))
