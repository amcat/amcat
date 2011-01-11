from amcat.test import amcattest, test_hierarchy
from amcat.model.ontology import codebook, ontologytoolkit
from amcat.db import dbtoolkit

from contextlib import contextmanager
from datetime import datetime
import logging; log = logging.getLogger(__name__)

TEST_CODEBOOKS = {
    -99 : ("TEST", [4000, 5000, 1, 2]),
    -98 : ("TEST", [5000, 4000, 2, 1]),
    }

TEST_PARENTS = {
    -99: {726 : 765, 1725: None },
    -98: {726 : 10433},
    }


TEST_REVERSED = {
    -99 : {2124 : True, 2083 : True, 1034 : False}
     }

TEST_CATEGORISATION = {
    -99 : {2124 : (10371, True),
           2083 : (10371, False),
           1034 : (10371, False),
           1721 : (10371, False),
	   1725 : (13898, False), # rutte = partijlid (1 voor 2)
	   (1725, datetime(2010,1,1)) : (13898, False), # rutte = nog steeds partijlid (-99 doet immers partij...)
           },
    -98 : {1725 : (18600, False), # rutte = min az (2 voor 1)
	   (1725, datetime(2010,1,1)) : (13897, False), # rutte = kamerlid (begin 2010 - 2 voor 1)
	   },
    }

class CodebookTest(amcattest.AmcatTestCase):
    
    def setUp(self):
        pass


    @contextmanager
    def createTestCodebook(self):
        try:
            self.db = dbtoolkit.amcatDB()
            for cid, (name, trees) in TEST_CODEBOOKS.items():
                self.db.insert("o_sets", dict(setid=cid, name=name), retrieveIdent=False)
                for i, tree in enumerate(trees):
                    self.db.insert("o_sets_classes", dict(setid=cid, classid=tree, rank=i+1), retrieveIdent=False)

            yield
        finally:
            self.db.rollback()

    def testCategorisation(self):
        with self.createTestCodebook():
            for cid, catdict in TEST_CATEGORISATION.items():
                c = codebook.Codebook(self.db, cid)
                for oid, (root, rev) in catdict.items():
		    if type(oid) == tuple:
			oid, date = oid
		    else:
			oid, date = oid, None
		    
                    root2, rev2 = c.categorise(oid, date, returnReverse=True)[0]
                    self.assertEqual(root2.id, root)
                    self.assertEqual(rev2, rev)

    def testParents(self):
        "Test whether .trees and .objects corresponds to test codebook"
        with self.createTestCodebook():
            for cid, objects in TEST_PARENTS.items():
                c = codebook.Codebook(self.db, cid)
                log.info(objects)
                for o, parent in objects.items():
                    log.info("%r.%s.parent is %r, should be %r" % (c, o, c.getParent(o), c.getObject(parent)))
                    self.assertEqual(c.getParent(o), c.getObject(parent))

class Stop:    
    def testReversed(self):
        "Test whether reversed matches expected values"
        with self.createTestCodebook():
            for cid, reverseddict in TEST_REVERSED.items():
                c = codebook.Codebook(self.db, cid)
                for oid, reversed in reverseddict.items():
                    self.assertEqual(c.isReversed(oid), reversed, msg="%r.%r.reversed? should be %r but is %r" % (c, oid, reversed, c.isReversed(oid)))
               


    def testTrees(self):
        "Test whether .trees and .objects corresponds to test codebook"
        with self.createTestCodebook():
            for cid, (name, trees) in TEST_CODEBOOKS.items():
                c = codebook.Codebook(self.db, cid)
                self.assertEqual(str(c), name)
                self.assertEqual([t.id for t in c.trees], trees)
                
    def testTreesConsistent(self):
        with self.createTestCodebook():
            for cid, (name, trees) in TEST_CODEBOOKS.items():
                c = codebook.Codebook(self.db, cid)
                c.uncache()
                c.cacheHierarchy()
                with self.db.disabled():
                    test_hierarchy.testConsistency(c)

    def xtestCategorisation(self):
        c = codebook.Codebook(self.db, 5001)
        db = dbtoolkit.amcatDB(profile=True)
        try:
            self.createTestCodebook(db)
        except:
            db.rollback()
            
        ##o = Object(self.db, 1560)
        #self.assertEqual([o2.id for o2 in c.getCategorisationPath(o)], [366, 10661])
        #self.assertEqual(c.categorise(o, depth=[1])[0].id, 366)
        #self.assertEqual(c.categorise(o, depth=[1], returnOmklap=True, returnObjects=False)[0], 1)

if __name__ == '__main__':
    import cProfile
    #cProfile.run('amcattest.main()')
    amcattest.main()
                    


        
        

