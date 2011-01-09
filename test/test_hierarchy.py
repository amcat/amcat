from amcat.model.ontology import hierarchy, ontologytoolkit
from amcat.model.ontology.object import Object
from amcat.test import amcattest

DUMMY_PARENTS = {2:3, 3:4, 5:4, 1:None, 4:None, 6:2, 7:5}
DUMMY_REVERSE = set([2,3,7])

TEST_PATH = {7 : [(7, False), (5, True), (4, True)],
             6 : [(6, False), (2, False), (3, True), (4, False)],
             }
TEST_CATEGORISE = {7 : ([4,5,7,7], [True, True, False, False]),
                   4 : ([4,4,4], [False,False,False]),
                   3 : ([4,3,3], [True, False, False]),
                   2 : ([4,3,2,2,2], [False, True, False, False, False]),
                   }


class DummyHierarchy(hierarchy.Hierarchy):
    def _getObjects(self):
        return DUMMY_PARENTS.keys()
    def _getParent(self, boundobject):
        return DUMMY_PARENTS.get(boundobject.id)
    def _isReversed(self, boundobject):
        return boundobject.id in DUMMY_REVERSE


class DummyDictHierarchy(hierarchy.DictHierarchy):
    def _getObjects(self):
        return DUMMY_PARENTS.keys()
    def _getParent(self, boundobject):
        return DUMMY_PARENTS.get(boundobject.id)


class DummyDictHierarchy2(hierarchy.DictHierarchy):
    def _getAllObjects(self):
        return DUMMY_PARENTS.items()
    
class HierarchyTest(amcattest.AmcatTestCase):
    def xtestPrint(self):
        h = DummyHierarchy(self.db)
        ontologytoolkit.printHierarchy(h)

    def testCategorisationPath(self):
        h = DummyHierarchy(self.db)
        for oid, path in TEST_PATH.items():
            p = [(o.id, r) for (o,r) in h.getPath(oid)]
            self.assertEqual(p, path)

    def testCategorisation(self):
        h = DummyHierarchy(self.db)
        for oid, (objs, omklaps) in   TEST_CATEGORISE.items():
            objs = map(h.getObject, objs)
            while objs:
                c = h.categorise(oid, depth=len(objs), returnObject=True, returnReverse=True)
                self.assertEqual(zip(objs, omklaps), h.categorise(oid, depth=len(objs), returnObject=True, returnReverse=True))
                self.assertEqual(objs, h.categorise(oid, depth=len(objs), returnObject=True, returnReverse=False))
                self.assertEqual(omklaps, h.categorise(oid, depth=len(objs), returnObject=False, returnReverse=True))                
                objs.pop(), omklaps.pop()

class Stop:
    def testGetObjectIdentity(self):
        "Test h.getObject(x) is x (identity) iff x.hierarchy=h"
        for cls in [hierarchy.Hierarchy, DummyDictHierarchy,DummyDictHierarchy2]:
            h = cls(self.db)
            h2 = cls(self.db)
            o = h.getObject(Object(self.db, 1))
            self.assertIs(o, h.getObject(o))
            self.assertNotIs(o, h2.getObject(o))
    def testGetObject(self):
        "Test getObject returns correct BoundInstance for all input"
        for cls in [hierarchy.Hierarchy, DummyDictHierarchy,DummyDictHierarchy2]:
            h = cls(self.db)
            o = hierarchy.BoundObject(h, Object(self.db, 1))
            self.assertEqual(o, h.getObject(o))
            self.assertEqual(o, h.getObject(o.id))
            self.assertEqual(o, h.getObject(o.objekt))
            self.assertEqual(o, h.getObject(o.objekt.id))
 
       
    def testBoundObjectEquality(self):
        "Test boundobjects b1 == b2 iff hierachies and objcets are equal"
        for cls in [hierarchy.Hierarchy, DummyDictHierarchy,DummyDictHierarchy2]:
            h = cls(self.db)
            h2 = cls(self.db)
            o = Object(self.db, 1)
            o2 = Object(self.db, 1)
            o3 = Object(self.db, 2)
            BO = hierarchy.BoundObject
            self.assertEqual(BO(h, o), BO(h,o))
            self.assertEqual(BO(h, o), BO(h,o2))
            self.assertNotEqual(BO(h, o), BO(h,o3))
            self.assertNotEqual(BO(h, o), BO(h2,o))
            self.assertNotEqual(BO(h, o), BO(h2,o2))
            self.assertNotEqual(BO(h, o), BO(h2,o3))
        

    def testGetParent(self):
        "Test getParent and getChildren on dummy hierarchy"
        with self.db.disabled(): # should not need db
            for cls in [DummyHierarchy, DummyDictHierarchy,DummyDictHierarchy2]:
                h = DummyHierarchy(self.db)
                self.assertItemsEqual(h.getObjects(), [h.getObject(x) for x in DUMMY_PARENTS])
                for c, p in DUMMY_PARENTS.items():
                    self.assertEqual(h.getParent(c), h.getObject(p))
                    if p is None:
                        self.assertIn(h.getObject(c), h.getRoots())
                    else:
                        self.assertIn(h.getObject(c), h.getChildren(p))

    def testConsistency(self):
        "Test whether dummy hierarchy is consistent"
        with self.db.disabled(): #should not need db
            for cls in [DummyHierarchy, DummyDictHierarchy,DummyDictHierarchy2]:
                testConsistency(cls(self.db))


class Inconsistent(Exception):
    def __init__(self, hierarchy, message):
        message = "%r inconsistent: %s" % (hierarchy, message)
        Exception.__init__(self, message)
        
def testConsistency(h):
    """Test whether h obeys the consistency rules for a hierarchy"""
    if not all(x.getParent() is None for x in h.getRoots()):
        raise Inconsistent(h,"Some roots have a parent")
    roots = set(h.getRoots())
    for o in h.getRoots():
        if h.getParent(o) is not None:
            raise Inconsistent(h,"Root %r has parent %r" % (o, o.getParent()))

    for o in h.getObjects():
        p = h.getParent(o)
        if o in roots:
            if p is not None:
                raise Inconsistent(h,"Tree %r inconsistent: Root %r has parent %r" %
                                (h, o, o.getParent()))
        else:
            if p is None:
                raise Inconsistent(h,"Non-Root %r has no parent" % ( o))
            children = set(h.getChildren(p))
            if o not in children:
                raise Inconsistent(h,"%r not in its parent (%r)'s children %r" % (o, p, children))

        for c in h.getChildren(o):
            p = c.getParent()
            if p != o:
                raise Inconsistent(h,"Object %r's child (%r)'s parent (%r) is not Object"
                                % (o, c, p))

    

        
if __name__ == '__main__':
    amcattest.main()
                    


