from amcat.models import Language
from amcat.tools import amcattest
from amcat.tools.amcattest import require_postgres
from amcat.tools.djangotoolkit import list_queries, db_supports_distinct_on, \
    bulk_insert_returning_ids


class TestDjangoToolkit(amcattest.AmCATTestCase):
    def test_queries(self):
        """Test the list_queries context manager"""
        u = amcattest.create_test_user()
        with list_queries() as l:
            amcattest.create_test_project(owner=u)
        self.assertEquals(len(l), 2) # create project, create role for owner

    def test_db_supports_distinct_on(self):
        self.assertTrue(db_supports_distinct_on() in (True, False))

    @require_postgres
    def test_bulk_insert_returning_ids(self):
        m1 = Language(label="test_bi_1")
        m2 = Language(label="test_bi_2")

        self.assertIsNone(m1.id)
        self.assertIsNone(m2.id)

        new_objects = bulk_insert_returning_ids([m1, m2])

        self.assertIsNone(m1.id)
        self.assertIsNone(m2.id)
        self.assertIsNotNone(new_objects[0].id)
        self.assertIsNotNone(new_objects[1].id)

        self.assertEqual("test_bi_1", Language.objects.get(id=new_objects[0].id).label)
        self.assertEqual("test_bi_2", Language.objects.get(id=new_objects[1].id).label)

