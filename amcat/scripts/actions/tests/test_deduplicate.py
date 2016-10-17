from amcat.scripts.actions.deduplicate import Deduplicate
from amcat.tools import amcattest
from amcat.tools.amcates import ES


class TestDedup(amcattest.AmCATTestCase):
    def do_test(self, articles, **options):
        ids = {a.id: i+1 for (i,a) in enumerate(articles)}
        s = amcattest.create_test_set(articles=articles)
        ES().flush()
        Deduplicate(articleset=s.id, **options).run()
        ES().flush()
        return {ids[a.id] for a in s.articles.all()}


    def test_fields(self):
        s = amcattest.create_test_set()
        self.assertEqual(set(Deduplicate(articleset=s.id).get_fields()), {'hash'})
        self.assertEqual(set(Deduplicate(articleset=s.id, ignore_medium=True).get_fields()),
                         {'text', 'title', 'byline', 'section', 'page', 'date'})
        self.assertEqual(set(Deduplicate(articleset=s.id, title_ratio=50).get_fields()),
                         {'hash'})
        self.assertEqual(set(Deduplicate(articleset=s.id, title_ratio=50, ignore_medium=True)
                             .get_fields()),
                         {'text', 'title', 'byline', 'section', 'page', 'date'})

        self.assertEqual(set(Deduplicate(articleset=s.id, title_ratio=50)
                             .get_fields(ignore_fuzzy=True)),
                         {'text', 'medium', 'byline', 'section', 'page', 'date'})
        self.assertEqual(set(Deduplicate(articleset=s.id, title_ratio=50, ignore_medium=True)
                             .get_fields(ignore_fuzzy=True)),
                         {'text', 'byline', 'section', 'page', 'date'})


    @amcattest.use_elastic
    def test_dedup(self):
        s = amcattest.create_test_set()
        m1, m2 = [amcattest.create_test_medium() for _x in range(2)]
        adict = dict(text="text", title="title", articleset=s, deduplicate=False)
        arts = [
            amcattest.create_test_article(medium=m1, pagenr=1, **adict),
            amcattest.create_test_article(medium=m1, pagenr=2, **adict),
            amcattest.create_test_article(medium=m2, pagenr=1, **adict),
            amcattest.create_test_article(medium=m2, pagenr=2, **adict),
            amcattest.create_test_article(medium=m2, pagenr=2, **adict)
            ]
        self.assertEqual(self.do_test(arts), {1,2,3,4})
        self.assertEqual(self.do_test(arts, dry_run=True), {1,2,3,4,5})
        self.assertEqual(self.do_test(arts, ignore_medium=True), {1,2})
        self.assertEqual(self.do_test(arts, ignore_page=True), {1,3})

    @amcattest.use_elastic
    def test_date(self):
        s = amcattest.create_test_set()
        m = amcattest.create_test_medium()
        adict = dict(text="text", title="title", articleset=s, medium=m)
        arts = [
            amcattest.create_test_article(date="2001-01-01", **adict),
            amcattest.create_test_article(date="2001-01-01 02:00", **adict),
            amcattest.create_test_article(date="2001-01-02", **adict),
            ]
        aids = [a.id for a in arts]

        self.assertEqual(self.do_test(arts), {1,2,3})
        self.assertEqual(self.do_test(arts, ignore_date=True), {1,3})

    @amcattest.use_elastic
    def test_fuzzy(self):
        s = amcattest.create_test_set()
        m = amcattest.create_test_medium()
        adict = dict(text="text", articleset=s, medium=m)
        arts = [
            amcattest.create_test_article(title="Dit is een test", **adict),
            amcattest.create_test_article(title="Dit is ook een test", **adict),
            amcattest.create_test_article(title="Dit is ook een tesdt", **adict),
            amcattest.create_test_article(title="Is dit een test?", **adict),

            ]
        self.assertEqual(self.do_test(arts, ignore_medium=True), {1,2,3,4})
        self.assertEqual(self.do_test(arts, ignore_medium=True, title_ratio=90), {1,2,4})
        self.assertEqual(self.do_test(arts, ignore_medium=True, title_ratio=80), {1,4})
        self.assertEqual(self.do_test(arts, ignore_medium=True, title_ratio=50), {1})
