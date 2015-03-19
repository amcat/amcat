from amcat.scripts.actions.get_queries import GetQueries
from amcat.tools import amcattest


class TestGetQueries(amcattest.AmCATTestCase):
    def test_label(self):
        from amcat.models import Language

        l = Language.objects.create(id=13, label='query')

        a = amcattest.create_test_code(label="test")
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        a = A.get_code(a.id)

        t = GetQueries(codebook=A.id).run()
        result = set(tuple(row) for row in t)
        self.assertEqual(result, {(a.id, "test", None)})

        a.add_label(l, "bla")

        t = GetQueries(codebook=A.id).run()
        result = set(tuple(row) for row in t)
        self.assertEqual(result, {(a.id, "test", "bla")})

    def todo_test_nqueries(self):
        from amcat.models.coding.code import Code
        from amcat.tools.caching import clear_cache
        from amcat.models import Language

        l = Language.objects.create(id=13, label='query')

        A = amcattest.create_test_codebook(name="A")
        codes = []
        N = 20
        for i in range(N):
            code = amcattest.create_test_code(label="test")
            A.add_code(code)
            code.add_label(l, "query")
            codes.append(code)

        clear_cache(Code)
        with self.checkMaxQueries(7):  # 3 for language, 2 for codes, 1 for bases, 1 for codebook
            t = GetQueries(codebook=A.id).run()
            result = set(tuple(row) for row in t)
        code = codes[3]
        self.assertIn((code.id, "test", "query"), result)
        self.assertEqual(len(result), N)