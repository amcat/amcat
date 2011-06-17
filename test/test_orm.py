# Testcases om te checken of Django ORM gebruikt kan worden
# als substituut voor "cachable"

from amcat.model import project, article, user
from amcat.model.set import Set
from amcat.test import amcattest
import datetime

class TestORM(amcattest.AmcatTestCase):

    def testEmptyCreation(self):
	"""Test performance of creating and manipulating 'empty' objects,
	i.e. objects without and db-derived values"""
	a, b = set(), set()
	for i in range(100000):
	    a.add(article.Article(None, i))
	    b.add(article.Article(None, i + 80000))
	self.assertEqual(len(a), 100000)
	self.assertEqual(len(b), 100000)
	self.assertEqual(len(a & b), 20000)
	

if __name__ == '__main__':
    # Standalone gebruik ORM automatisch getest door CLI test case 
    amcattest.main()
