from django.http import QueryDict
from amcat.tools import amcattest
from amcat.tools.djangotoolkit import get_related_models, list_queries, to_querydict, get_or_create, \
    db_supports_distinct_on


class TestDjangoToolkit(amcattest.AmCATTestCase):
    def test_related_models(self):
        """Test get_related_models function. Note: depends on the actual amcat.models"""

        for start, stoplist, result in [
            (('Sentence',), ('Project',), ['Article', 'Language', 'Medium', 'Project', 'Sentence']),
            ]:

            related = get_related_models(start, stoplist)
            related_names = set(r.__name__ for r in related)
            self.assertEqual(related_names, set(result))

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