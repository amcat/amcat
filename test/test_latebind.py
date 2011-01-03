from amcat.test import amcattest
from amcat.tools.cachable.latebind import LB

class TestLateBind(amcattest.AmcatTestCase):

    def testbind(self):
        l = LB("Language")
        l2 = LB("Language", "language")
        l3 = LB("Language", "language", "amcat.model")

        from  amcat.model.language import Language
        
        u, u2, u3  = l(), l2(), l3()

        self.assertEqual(u, Language)
        self.assertEqual(u2, Language)
        self.assertEqual(u3, Language)
        
if __name__ == '__main__':
    amcattest.main()
