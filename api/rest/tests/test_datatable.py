import re
from amcat.tools import amcattest
from api.rest.datatable import Datatable, order_by

from api.rest.viewsets import ArticleSetViewSet
from api.rest.viewsets import CodingSchemaFieldViewSet
from api.rest.resources import UserResource
from api.rest.resources import ProjectResource
from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer
from amcat.models import Project


class TestDatatable(amcattest.AmCATTestCase):
    PROJECT_FIELDS = {'id', 'name', 'description', 'insert_date', 'owner', 'r_plugins_enabled',
                      'insert_user', 'guest_role', 'active', 'favourite', 'last_visited_at', 'display_columns'}

    def test_viewset(self):
        """Can ViewSets also be used?"""
        dt = Datatable(CodingSchemaFieldViewSet, url_kwargs={"project": 1})
        self.assertTrue(dt.url.startswith("/api/v4/projects/1/codingschemafields/"))
        self.assertEqual(set(dt.fields), {
            'id', 'codingschema', 'fieldnr', 'label', 'required', 'fieldtype',
            'codebook', 'split_codebook', 'default',
        })

    def test_url(self):
        d = Datatable(UserResource)
        self.assertEqual(d.url, '/api/v4/user?format=json')

    def test_fields(self):
        d = Datatable(ProjectResource)
        self.assertEqual(set(d.fields), TestDatatable.PROJECT_FIELDS)

        # Test order of fields.
        class TestSerializer(AmCATModelSerializer):
            class Meta:
                model = Project
                fields = ('name', 'description', 'id')

        class TestResource(AmCATResource):
            model = Project
            serializer_class = TestSerializer

        d = Datatable(TestResource)
        self.assertEqual(('name', 'description', 'id'), tuple(d.fields))

    def test_hide(self):
        d = Datatable(ProjectResource)

        # Nothing hidden by default
        self.assertEqual(set(d.fields), TestDatatable.PROJECT_FIELDS)

        # Hide some fields..
        hide = {"id", "name", "insert_user"}
        d = d.hide(*hide)

        self.assertEqual(set(d.fields), TestDatatable.PROJECT_FIELDS - hide)

    def test_filter(self):
        d = Datatable(UserResource)
        s = '/api/v4/user?format=json'

        # No filter
        self.assertEqual(d.url, s)

        # One filter
        d = d.filter(id=1)
        self.assertEqual(d.url, s + "&id=1")

        # Multiple filters
        d = d.filter(id=2)
        self.assertEqual(d.url, s + "&id=1&id=2")

        d = Datatable(UserResource).filter(id=[1, 2])
        self.assertEqual(d.url, s + "&id=1&id=2")

        # Test can allow illegal filter field as extra_arg

        d = Datatable(UserResource).add_arguments(q=[1, 2])
        self.assertEqual(d.url, s + "&q=1&q=2")

    def test_js(self):
        d = Datatable(ProjectResource)
        js = d.get_js()

    def test_get_name(self):
        d = Datatable(ProjectResource).filter(id=[1, "#$^"])
        self.assertTrue(len(d.get_name()) >= 1)
        self.assertFalse(re.match(r'[^0-9A-Za-z_:.-]', d.get_name()))
        self.assertTrue(re.match(r'^[A-Za-z]', d.get_name()))

    def test_order_by_func(self):
        self.assertEquals(("field", "desc"), order_by("-field"))
        self.assertEquals(("f", "asc"), order_by("+f"))

    def test_order_by(self):
        d = Datatable(ProjectResource).order_by("name")
        self.assertTrue("name" in str(d))
        self.assertTrue('["name", "asc"]' in str(d))
        self.assertTrue('["name", "desc"]' in str(d.order_by("-name")))

        with self.assertRaises(ValueError):
            d.order_by("bla")

        with self.assertRaises(ValueError):
            d.order_by("?name")

    def test_search(self):
        # Resources are not searchable (yet?)
        d = Datatable(ProjectResource)
        self.assertIn('"searching": false', str(d))

        # Articleset viewsets are searchable
        d = Datatable(ArticleSetViewSet, url_kwargs={"project": 1})
        self.assertIn('"searching": true', str(d))
