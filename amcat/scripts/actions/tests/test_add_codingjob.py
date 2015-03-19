from amcat.scripts.actions.add_codingjob import AddCodingJob
from amcat.tools import amcattest

class TestAddJob(amcattest.AmCATTestCase):
    def _get_args(self, n_articles):
        s = amcattest.create_test_set(articles=n_articles)
        u = amcattest.create_test_user()
        uschema = amcattest.create_test_schema()
        aschema = amcattest.create_test_schema(isarticleschema=True)
        return dict(project=s.project.id, articleset=s.id, coder=u.id, articleschema=aschema.id, unitschema=uschema.id, insertuser=u.id)

    def todo_test_add(self):
        j = AddCodingJob.run_script(name="test", **self._get_args(10))
        self.assertEqual(j.articleset.articles.count(), 10)
        a = j.articleset.articles.all()[0]
        self.assertTrue(a.sentences.exists(), "No sentences have been created")

    def test_job_size(self):
        jobs = AddCodingJob.run_script(name="test", job_size=4, **self._get_args(10))
        self.assertEqual(len(jobs), 3)
        self.assertEqual(sorted(j.articleset.articles.count() for j in jobs), sorted([4, 4, 2]))
        self.assertEqual({j.name for j in jobs}, {"test - 1", "test - 2", "test - 3"})