# Testcases om te checken of Django ORM gebruikt kan worden
# als substituut voor "cachable"

from amcat.model import project, article
from django.utils import unittest

import datetime

class TestORM(unittest.TestCase):

    def testEmptyCreation(self):
        """Test performance of creating and manipulating 'empty' objects,
        i.e. objects without and db-derived values"""
        a, b = set(), set()

        for i in range(100000):
            a_art = article.Article()
            a_art.id = i

            b_art = article.Article()
            b_art.id = i + 100001

            a.add(a_art)
            b.add(b_art)
        
        #for i in range(100000):
        #    a.add(article.Article(None, i))
        #    b.add(article.Article(None, i + 80000))

        self.assertEqual(len(a), 100000)
        self.assertEqual(len(b), 100000)
        #self.assertEqual(len(a & b), 20000)
    

if __name__ == '__main__':
    # Standalone gebruik ORM automatisch getest door CLI test case 
    unittest.main()
