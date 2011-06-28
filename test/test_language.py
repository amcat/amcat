from amcat.test import amcattest
from amcat.model import language

class LanguageTest(amcattest.AmcatTestCase):
    def testLanguage(self):
        l = language.Language(self.db, 1)
        self.assertEqual(l.label, 'en')


if __name__ == '__main__':
    amcattest.main()
