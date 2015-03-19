from amcat.scripts.actions.deduplicate import Deduplicate
from amcat.tools import amcattest
from amcat.tools.amcates import ES


class TestDedup(amcattest.AmCATTestCase):
    def do_test(self, articles, **options):
        s = amcattest.create_test_set(articles=articles)
        ES().flush()
        Deduplicate(articleset=s.id, **options).run()
        ES().flush()
        return set(s.articles.values_list("pk", flat=True))


    def test_fields(self):
        s = amcattest.create_test_set()
        self.assertEqual(set(Deduplicate(articleset=s.id).get_fields()), {'hash'})
        self.assertEqual(set(Deduplicate(articleset=s.id, ignore_medium=True).get_fields()),
                         {'text', 'headline', 'byline', 'section', 'page', 'date'})
        self.assertEqual(set(Deduplicate(articleset=s.id, headline_ratio=50).get_fields()),
                         {'hash'})
        self.assertEqual(set(Deduplicate(articleset=s.id, headline_ratio=50, ignore_medium=True)
                             .get_fields()),
                         {'text', 'headline', 'byline', 'section', 'page', 'date'})

        self.assertEqual(set(Deduplicate(articleset=s.id, headline_ratio=50)
                             .get_fields(ignore_fuzzy=True)),
                         {'text', 'medium', 'byline', 'section', 'page', 'date'})
        self.assertEqual(set(Deduplicate(articleset=s.id, headline_ratio=50, ignore_medium=True)
                             .get_fields(ignore_fuzzy=True)),
                         {'text', 'byline', 'section', 'page', 'date'})


    @amcattest.use_elastic
    def test_dedup(self):
        s = amcattest.create_test_set()
        m1, m2 = [amcattest.create_test_medium() for _x in range(2)]
        arts = [
            amcattest.create_test_article(articleset=s, medium=m1, pagenr=1, id=1),
            amcattest.create_test_article(articleset=s, medium=m1, pagenr=2, id=2),
            amcattest.create_test_article(articleset=s, medium=m2, pagenr=1, id=3),
            amcattest.create_test_article(articleset=s, medium=m2, pagenr=2, id=4),
            amcattest.create_test_article(articleset=s, medium=m2, pagenr=2, id=5)
            ]
        self.assertEqual(self.do_test(arts), {1,2,3,4})
        self.assertEqual(self.do_test(arts, dry_run=True), {1,2,3,4,5})
        self.assertEqual(self.do_test(arts, ignore_medium=True), {1,2})
        self.assertEqual(self.do_test(arts, ignore_page=True), {1,3})

    @amcattest.use_elastic
    def test_date(self):
        s = amcattest.create_test_set()
        m = amcattest.create_test_medium()
        arts = [
            amcattest.create_test_article(id=1, articleset=s, medium=m, date="2001-01-01"),
            amcattest.create_test_article(id=2, articleset=s, medium=m, date="2001-01-01 02:00"),
            amcattest.create_test_article(id=3, articleset=s, medium=m, date="2001-01-02"),
            ]
        aids = [a.id for a in arts]

        self.assertEqual(self.do_test(arts), {1,2,3})
        self.assertEqual(self.do_test(arts, ignore_date=True), {1,3})

    @amcattest.use_elastic
    def test_fuzzy(self):
        s = amcattest.create_test_set()
        m = amcattest.create_test_medium()
        arts = [
            amcattest.create_test_article(id=1, articleset=s, medium=m, headline="Dit is een test"),
            amcattest.create_test_article(id=2, articleset=s, medium=m, headline="Dit is ook een test"),
            amcattest.create_test_article(id=3, articleset=s, medium=m, headline="Dit is ook een tesdt"),
            amcattest.create_test_article(id=4, articleset=s, medium=m, headline="Is dit een test?"),

            ]
        self.assertEqual(self.do_test(arts, ignore_medium=True), {1,2,3,4})
        self.assertEqual(self.do_test(arts, ignore_medium=True, headline_ratio=90), {1,2,4})
        self.assertEqual(self.do_test(arts, ignore_medium=True, headline_ratio=80), {1,4})
        self.assertEqual(self.do_test(arts, ignore_medium=True, headline_ratio=50), {1})