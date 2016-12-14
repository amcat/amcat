from amcat.tools import amcattest
from api.rest.viewsets import CodedArticleSerializer


class TestCodedArticleSerializer(amcattest.AmCATTestCase):
    # Simulating request
    class View(object):
        def get_queryset(self):
            return self.queryset

        def filter_queryset(self, queryset):
            return queryset

        def __init__(self, objs):
            self.queryset = objs

    def _get_serializer(self, coded_article):
        return CodedArticleSerializer(context={"view" : self.View(coded_article)})

    def test_fields(self):
        c = amcattest.create_test_job()
        a = c.articleset.articles.all()[0]

        a.set_property("length_int", 3)
        a.set_property("pagenr_int", 3)
        a.save()

        ca = c.coded_articles.all()[0]
        s = self._get_serializer(c.coded_articles.all())

        self.assertEqual(a.title, s.get_title(ca))
        self.assertEqual(a.date, s.get_date(ca))
        self.assertEqual(a.get_property("pagenr_int"), s.get_pagenr(ca))

    def test_n_queries(self):
        c = amcattest.create_test_job(10)
        s = self._get_serializer(c.coded_articles.all())
        ca1, ca2, ca3 = c.coded_articles.all()[0:3]

        with self.checkMaxQueries(1):
            s.get_title(ca1)
            s.get_title(ca2)
            s.get_title(ca3)
            s.get_date(ca3)
            s.get_pagenr(ca3)
