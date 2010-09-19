import dbtoolkit, unittest, batch

class TestSystem(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testArticles(self):
        b = batch.Batch(self.db, 5373)
        self.assertTrue(len(b.articles) > 0)

if __name__ == '__main__':
    unittest.main()
