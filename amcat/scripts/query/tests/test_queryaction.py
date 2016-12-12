import uuid

from amcat.models import ArticleSet
from amcat.scripts.query import QueryAction
from amcat.scripts.query.queryaction import NotInCacheError
from amcat.tools import amcattest


class FooBarQueryAction(QueryAction):
    output_types = (
        ("text/foo", "Foo"),
        ("text/bar", "Bar")
    )

    def run(self, form):
        pass


class TestQueryAction(amcattest.AmCATTestCase):
    def test_cache(self):
        project = amcattest.create_test_project()
        aset = amcattest.create_test_set(project=project)
        user = project.owner

        # Defeat caches remaining after tests..
        query = str(uuid.uuid4())

        asets = ArticleSet.objects.filter(id__in=[aset.id])
        qa = FooBarQueryAction(user, project, asets, data={
            "query": query,
            "output_type": "text/foo"
        })

        form = qa.get_form()
        form.full_clean()

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["output_type"], "text/foo")
        self.assertRaises(NotInCacheError, qa.get_cache)

        # Test small string
        qa.set_cache("abc")
        self.assertEqual(qa.get_cache(), "abc")

        # Test complex number
        qa.set_cache(2+1j)
        self.assertEqual(qa.get_cache(), 2+1j)

        # Test very large easily compressible string (5 MiB)
        large_string = "a" * (1024 * 1024 * 5)
        qa.set_cache(large_string)
        self.assertEqual(qa.get_cache(), large_string)


        # If we change only output_type, it should not raise an error
        qa.set_cache("a")
        self.assertEqual(qa.get_cache(), "a")

        qa = FooBarQueryAction(user, project, asets, data={
            "query": query,
            "output_type": "text/bar"
        })

        self.assertEqual(qa.get_cache(), "a")

        # Change the user. Does it yield a cache error?
        user = amcattest.create_test_user()
        qa = FooBarQueryAction(user, project, asets, data={
            "query": query,
            "output_type": "text/foo"
        })
        self.assertRaises(NotInCacheError, qa.get_cache)
