import logging; log = logging.getLogger(__name__)
from amcat.test import amcattest
from amcat.model.coding import codingjob, codedarticle, codingjobset
from amcat.tools.cachable import cacher

from amcat.tools.logging import amcatlogging; amcatlogging.debugModule

class TestCodedArticle(amcattest.AmcatTestCase):
    def testStatus(self):
        "Test whether status can be queried and has correct str representation"
        ca = codedarticle.CodedArticle(self.db, 1)
        self.assertEqual(ca.status.id, 0)
        self.assertEqual(str(ca.status), "not started")
        
        
        
if __name__ == '__main__':
    amcattest.main()
