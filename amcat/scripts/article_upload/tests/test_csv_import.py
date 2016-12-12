
import csv
import unittest
from amcat.models import ArticleSet
from amcat.scripts.article_upload.csv_import import CSV
from amcat.tools import amcattest


class TestCSV(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_csv(self):
        header = ('kop', 'datum', 'tekst', 'pagina')
        data = [('kop1', '2001-01-01', 'text1', '12'), ('kop2', '10 maart 1980', 'text2', None)]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum", pagenr='pagina')
        self.assertEqual(len(articles), 2)

        # Scraper is not guarenteed to return articles in order.
        self.assertEqual({articles[0].headline, articles[1].headline}, {'kop1', 'kop2'})
        self.assertEqual({articles[0].pagenr, articles[1].pagenr}, {12, None})

        date1 = articles[0].date.isoformat()[:10]
        date2 = articles[1].date.isoformat()[:10]
        self.assertTrue('1980-03-10' in {date1, date2})

    @amcattest.use_elastic
    def test_text(self):
        header = ('kop', 'datum', 'tekst')
        data = [('kop1', '2001-01-01', '')]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].text, "")



    @unittest.skip("Controller is a mess")
    def test_parents(self):
        header = ('kop', 'datum', 'tekst', 'id', 'parent', 'van')
        data = [
            ('kop1', '2001-01-01', 'text1', "7", "12", 'piet'),
            ('kop2', '2001-01-01', 'text2', "12", None, 'jan')
        ]
        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum",
                                 externalid='id', parent_externalid='parent', author='van')


        # for strange reasons, it seems that the order is sometimes messed up
        # since this is not something we care about, we order the results
        articles = sorted(articles, key=lambda a: a.externalid)

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].parent, articles[1])
        self.assertEqual(articles[0].externalid, 7)
        self.assertEqual(articles[0].author, 'piet')
        self.assertEqual(articles[0].addressee, None)

        self.assertEqual(articles[1].parent, None)
        self.assertEqual(articles[1].externalid, 12)
        self.assertEqual(articles[1].author, 'jan')
        self.assertEqual(articles[1].addressee, None)

        articles = _run_test_csv(header, data, text="tekst", headline="kop", date="datum",
                                 externalid='id', parent_externalid='parent', author='van',
                                 addressee_from_parent=True)

        # see above
        articles = sorted(articles, key=lambda a: a.externalid)

        self.assertEqual(articles[0].author, 'piet')
        self.assertEqual(articles[0].addressee, 'jan')
        self.assertEqual(articles[1].author, 'jan')
        self.assertEqual(articles[1].addressee, None)


    @amcattest.use_elastic
    def test_date_format(self):
        # Stump class to test future 'date format' option, if needed. Currently just checks that
        # a variety of formats load correctly.
        header = "date", "text"

        for datestr, dateformat, expected in [
            ("2001-01-01", None, "2001-01-01"),
            ("10/03/80", None, "1980-03-10"),
            ("15/08/2008", None, "2008-08-15"),
        ]:
            data = [(datestr, "text")]
            a, = _run_test_csv(header, data, date="date", text="text")
            self.assertEqual(a.date.isoformat()[:10], expected)

def get_field_map(**kwargs):
    return dict((k, {"value":  v, "type": "field"}) for k, v in kwargs.items())


def _run_test_csv(header, rows, **options):
    project = amcattest.create_test_project()
    articleset = amcattest.create_test_set(project=project)

    from tempfile import NamedTemporaryFile
    from django.core.files import File

    with NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in [header] + list(rows):
            w.writerow([field and field for field in row])
        f.flush()

        set = CSV(dict(file=File(open(f.name, "rb")), encoding=0, project=project.id,
                       medium_name=options.pop("medium_name", 'testmedium'),
                       articleset=articleset.id, **options)).run()

    return ArticleSet.objects.get(id=set[0]).articles.all()
