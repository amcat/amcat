from amcat.models import CodingJob
from amcat.scripts.actions.delete_codingjob import DeleteCodingJob
from amcat.tools import amcattest


class TestDeleteCodingJob(amcattest.AmCATTestCase):
    def test_delete(self):
        """Simple deletion of a job"""
        from amcat.models import ArticleSet, Coding
        s = amcattest.create_test_set(articles=5)
        j = amcattest.create_test_job(articleset=s)
        c = amcattest.create_test_coding(codingjob=j)
        self.assertTrue(CodingJob.objects.filter(pk=j.id).exists())
        self.assertTrue(ArticleSet.objects.filter(pk=s.id).exists())
        self.assertTrue(Coding.objects.filter(pk=c.id).exists())
        DeleteCodingJob(job=j.id).run()
        self.assertFalse(CodingJob.objects.filter(pk=j.id).exists())
        self.assertFalse(ArticleSet.objects.filter(pk=s.id).exists())
        self.assertFalse(Coding.objects.filter(pk=c.id).exists())

    def test_delete_setinuse(self):
        """Delete a job whose set is in use somewhere else"""
        from amcat.models import ArticleSet
        s = amcattest.create_test_set(articles=5)
        j = amcattest.create_test_job(articleset=s)
        j2 = amcattest.create_test_job(articleset=s)# use same article set
        DeleteCodingJob(job=j.id).run()
        self.assertFalse(CodingJob.objects.filter(pk=j.id).exists())
        self.assertEquals(j2.articleset, s)
        self.assertTrue(ArticleSet.objects.filter(pk=s.id).exists())