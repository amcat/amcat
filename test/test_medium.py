from amcat.test import amcattest
from amcat.model import medium

class MediumTest(amcattest.AmcatTestCase):

    def testMedia(self):
        m = medium.Media(self.db)
        self.assertEqual(m.lookupName("ZZZ"), None)
        self.assertEqual(m.lookupName("De Telegraaf").id, 6)
        self.assertEqual(m.lookupName("   DE telegrAAF   ").id, 6)

if __name__ == '__main__':
    amcattest.main()
