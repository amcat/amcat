from amcat.test import amcattest, test_hierarchy
from amcat.model.ontology import codebook, ontologytoolkit
from amcat.db import dbtoolkit


TEST_CODEBOOKS = [
    (-99, "TEST", [4000, 6000], {726 : (765, False)}),
    (-98, "TEST", [6000, 4000], {726 : (1370, False)}),
    ]

class CodebookTest(amcattest.AmcatTestCase):

    def createTestCodebook(self, db):
        for cid, name, trees, objects in TEST_CODEBOOKS:
            db.insert("o_sets", dict(setid=cid, name=name), retrieveIdent=False)
            for i, tree in enumerate(trees):
                db.insert("o_sets_classes", dict(setid=cid, classid=tree, rank=i+1), retrieveIdent=False)
            for o in objects:
                db.insert("o_sets_objects", dict(setid=cid, objectid=o), retrieveIdent=False)
    
    def testPrint(self):
        c = codebook.Codebook(self.db, 5000)
        ontologytoolkit.printHierarchy(c)

class Stop:
        
    def testTreesObjects(self):
        "Test whether .trees and .objects corresponds to test codebook"
        db = dbtoolkit.amcatDB(profile=True)
        try:
            self.createTestCodebook(db)
            for cid, name, trees, objects in TEST_CODEBOOKS:
                c = codebook.Codebook(db, cid)
                self.assertEqual(str(c), name)
                self.assertEqual([t.id for t in c.trees], trees)
                self.assertItemsEqual([t.id for t in c.getObjects()], objects.keys())
                for o, (parent, reversed) in objects.items():
                    self.assertEqual(c.getParent(o), c.getObject(parent))
        finally:
            db.rollback()

    def testTreesConsistent(self):
        db = dbtoolkit.amcatDB(profile=True)
        try:
            self.createTestCodebook(db)
            for cid, name, trees, objects in TEST_CODEBOOKS:
                c = codebook.Codebook(db, cid)
                c.uncache()
                c.cacheHierarchy()
                with db.disabled():
                    test_hierarchy.testConsistency(c)
        finally:
            db.rollback()

    def testCategorisation(self):
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
                    


        
        

