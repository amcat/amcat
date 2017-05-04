import datetime
import os
from amcat.scripts.article_upload.plugins.defacto_student import get_html, split_html, get_article, \
    get_meta, get_title, get_section, get_body
from amcat.tools import amcattest


class TestDeFactoStudent(amcattest.AmCATTestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files', 'defacto')
        self.test1 = os.path.join(self.test_dir, 'DeFacto-Campus - Ausdruck1.htm')
        self.test1_html = get_html(open(self.test1, "rb").read())
        self.test2 = os.path.join(self.test_dir, 'DeFacto-Campus - Ausdruck2.htm')
        self.test2_html = get_html(open(self.test2, "rb").read())

    def test_split(self):
        elems = split_html(self.test1_html)
        self.assertEqual(len(elems), 21)

    def test_articles(self):
        arts = [get_article(x) for x in split_html(self.test1_html)]
        arts2 = [get_article(x) for x in split_html(self.test2_html)]
        self.assertEqual(arts2[-1].title, 'Cafe Puls News 08:00 (08:00) - Peter Kaiser wird angelobt')
        self.assertEqual(arts2[-1].date, datetime.datetime(2013,4,2,8,0))

    def test_parse(self):
        elems = split_html(self.test1_html)

        self.assertEqual(get_meta(elems[0]), ("Der Standard", datetime.datetime(2013,4,2), 1))
        self.assertEqual(get_title(elems[0]), u'SP und VP k\xf6nnten dritte Partei f\xfcr Koalition brauchen')
        self.assertEqual(get_section(elems[0]), u'SEITE 1')
        body = get_body(elems[0])
        self.assertTrue(body.startswith(u'Wien - SP\xd6 und \xd6VP'))
        self.assertTrue(body.endswith("hoffen. (red) Seite 7"))
        self.assertEqual(len(body.split("\n\n")), 3) # no of paragraphs

        self.assertEqual(get_meta(elems[1]), ("Wiener Zeitung", datetime.datetime(2013,4,2), 3))
        self.assertEqual(get_title(elems[1]), u'Politique autrichienne als Vorbild')
        self.assertEqual(get_section(elems[1]), 'Europa@welt')
        body = get_body(elems[1])
        self.assertTrue(body.startswith(u'Frankreichs Botschafter'))
        self.assertTrue(body.endswith("Treffen im Oktober 2012. epa"))
        self.assertEqual(len(body.split("\n\n")), 28) # no of paragraphs

        body = get_body(elems[-1])
        self.assertTrue('<a href="mailto:peter.filzmaier@donau-uni.ac.at">peter.filzmaier@donau-uni.ac.at</a>' in body)
