import dbtoolkit, amcattest, article

class TestArticle(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testProperties(self):
        for (aid, batchid, sourceid, section, headline) in [
            (353570, 8, 5, 'Economie;', "Lezers Brabants Nieuwsblad zijn 'massaal' ongerust"),
            ]:

            a = article.Article(self.db, aid)
            self.assertEqual(a.id, aid)
            self.assertEqual(a.source.id, sourceid)
            self.assertEqual(a.batch.id, batchid)
            self.assertEqual(a.section, section)
            self.assertEqual(a.headline, headline)
    
        
if __name__ == '__main__':
    amcattest.main()
