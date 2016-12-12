import csv
import json
import unittest

from amcat.scripts.article_upload.csv_import import CSV
from amcat.scripts.article_upload.upload import UploadForm
from amcat.tools import amcattest
from settings import ES_MAPPING_TYPE_PRIMITIVES


class TestCSV(amcattest.AmCATTestCase):
    @amcattest.use_elastic
    def test_csv(self):
        header = ('kop', 'datum', 'tekst', 'pagina')
        data = [('kop1', '2001-01-01', 'text1', '12'), ('kop2', '10 maart 1980', 'text2', None)]
        field_map = _get_field_map(
            title="kop",
            date="datum",
            text="tekst",
            page="pagina"
        )
        articles = _run_test_csv(header, data, field_map)
        self.assertEqual(len(articles), 2)

        # Scraper is not guarenteed to return articles in order.
        self.assertEqual({articles[0].title, articles[1].title}, {'kop1', 'kop2'})
        self.assertEqual({articles[0].properties['page'], articles[1].properties['page']}, {"12", ''})

        date1 = articles[0].date.isoformat()[:10]
        date2 = articles[1].date.isoformat()[:10]
        self.assertTrue('1980-03-10' in {date1, date2})

    @amcattest.use_elastic
    def test_text(self):
        header = ('kop', 'datum', 'tekst')
        data = [('kop1', '2001-01-01', '')]
        articles = _run_test_csv(header, data, _get_field_map(text="tekst", title="kop", date="datum"))
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].text, "")

    @amcattest.use_elastic
    def test_types(self):
        header = ('kop', 'datum', 'tekst', 'age', 'length', 'now')
        data = [('kop1', '2001-01-01', '', 7, 1.5, "1 mei 2012")]
        articles = _run_test_csv(header, data, _get_field_map(text="tekst",
                                                              title="kop",
                                                              date="datum",
                                                              age_int="age",
                                                              length_num="length",
                                                              now_date="now"))
        self.assertEqual(len(articles), 1)
        self.assertIsInstance(articles[0].properties['age_int'], ES_MAPPING_TYPE_PRIMITIVES['int'])
        self.assertIsInstance(articles[0].properties['length_num'], ES_MAPPING_TYPE_PRIMITIVES['num'])
        self.assertIsInstance(articles[0].properties['now_date'], ES_MAPPING_TYPE_PRIMITIVES['date'])

    @amcattest.use_elastic
    def test_literals(self):
        header = ('kop', 'datum', 'tekst')
        data = [('kop1', '2001-01-01', '')]
        field_map = _get_field_map(text="tekst", title="kop")
        field_map["date"] = {"type": "literal", "value": "2016-12-12"}
        articles = _run_test_csv(header, data, field_map)
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].date.isoformat()[:10], "2016-12-12")

    @unittest.skip("Behavior not specified.")
    def test_parents(self):
        self.fail()

    @amcattest.use_elastic
    def test_date_format(self):
        # Stump class to test future 'date format' option, if needed. Currently just checks that
        # a variety of formats load correctly.
        header = ("date",)

        for datestr, dateformat, expected in [
            ("2001-01-01", None, "2001-01-01"),
            ("10/03/80", None, "1980-03-10"),
            ("15/08/2008", None, "2008-08-15"),
        ]:
            data = [(datestr,)]
            field_map = _get_field_map(date="date")
            field_map["title"] = {"type": "literal", "value": "title"}
            field_map["text"] = {"type": "literal", "value": "-"}
            a, = _run_test_csv(header, data, field_map)
            self.assertEqual(a.date.isoformat()[:10], expected)


def _get_field_map(**kwargs):
    return dict((k, {"value":  v, "type": "field"}) for k, v in kwargs.items())


def _run_test_csv(header, rows, field_map, **options):
    project = amcattest.create_test_project()

    from tempfile import NamedTemporaryFile
    from django.core.files import File

    with NamedTemporaryFile(suffix=".txt", mode="w", encoding="utf-8") as f:
        w = csv.writer(f)
        for row in [header] + list(rows):
            w.writerow([field and field for field in row])
        f.flush()
        form = UploadForm(
            files={
                "file": File(open(f.name, "rb")),
            },
            data={
                "project": project.id,
                "field_map": json.dumps(field_map),
                "encoding": "UTF-8"
            }
        )
        form.full_clean()
        if not form.is_valid():
            raise Exception(form.errors)
        set = CSV(form).run()

    return set.articles.all()
