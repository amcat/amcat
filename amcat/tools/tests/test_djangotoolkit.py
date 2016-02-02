from __future__ import absolute_import
from __future__ import unicode_literals
from django.http import QueryDict
from amcat.models import Medium

from amcat.tools import amcattest
from amcat.tools.amcattest import create_test_medium, create_test_article, require_postgres
from amcat.tools.djangotoolkit import list_queries, to_querydict, get_or_create, \
    db_supports_distinct_on, get_model_field, bulk_insert_returning_ids


class TestDjangoToolkit(amcattest.AmCATTestCase):
    def test_queries(self):
        """Test the list_queries context manager"""
        u = amcattest.create_test_user()
        with list_queries() as l:
            amcattest.create_test_project(owner=u)
        #query_list_to_table(l, output=print)
        self.assertEquals(len(l), 2) # create project, create role for owner

    def test_from_querydict(self):
        di = dict(a=1, b=[2,3])
        self.assertEqual(to_querydict(di), QueryDict("a=1&b=2&b=3"))

    def test_to_querydict(self):
        d = to_querydict(dict(a=1, b=[2,3]))
        self.assertEqual(d.get("a"), "1")
        self.assertEqual(d.get("b"), "3")
        self.assertEqual(d.getlist("a"), ["1"])
        self.assertEqual(d.getlist("b"), ["2","3"])

        self.assertFalse(d._mutable)
        d = to_querydict({}, mutable=False)
        self.assertFalse(d._mutable)
        d = to_querydict({}, mutable=True)
        self.assertTrue(d._mutable)


    def test_get_or_create(self):
        """Test the get or create operation"""
        from amcat.models.medium import Medium
        name = "dsafdsafdsafDSA_amcat_test_medium"
        Medium.objects.filter(name=name).delete()
        self.assertRaises(Medium.DoesNotExist, Medium.objects.get, name=name)
        m = get_or_create(Medium, name=name)
        self.assertEqual(m.name, name)
        m2 = get_or_create(Medium, name=name)
        self.assertEqual(m, m2)

    def test_db_supports_distinct_on(self):
        self.assertTrue(db_supports_distinct_on() in (True, False))

    def test_get_model_field(self):
        article = create_test_article(text="abc", medium=create_test_medium(name="The Guardian"))

        self.assertEqual(article.medium.name, "The Guardian")
        self.assertEqual(get_model_field(article, "medium__name"), "The Guardian")
        self.assertEqual(get_model_field(article, "medium"), article.medium)
        self.assertEqual(get_model_field(article, "text"), "abc")

    @require_postgres
    def test_bulk_insert_returning_ids(self):
        m1 = Medium(name="test_bi_1")
        m2 = Medium(name="test_bi_2")

        self.assertIsNone(m1.id)
        self.assertIsNone(m2.id)

        new_objects = bulk_insert_returning_ids([m1, m2])

        self.assertIsNone(m1.id)
        self.assertIsNone(m2.id)
        self.assertIsNotNone(new_objects[0].id)
        self.assertIsNotNone(new_objects[1].id)

        self.assertEqual("test_bi_1", Medium.objects.get(id=new_objects[0].id).name)
        self.assertEqual("test_bi_2", Medium.objects.get(id=new_objects[1].id).name)

