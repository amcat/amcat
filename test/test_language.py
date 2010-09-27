import dbtoolkit, unittest, amcattest, language

class LanguageTest(amcattest.AmcatTestCase):
    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
    def testLanguage(self):
        l = language.Language(self.db, 1)
        self.assertEqual(l.label, 'en')


if __name__ == '__main__':
    unittest.main()
