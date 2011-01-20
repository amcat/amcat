from __future__ import print_function

from amcat.test import amcattest, test_hierarchy, test_object
from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree


class TestTree(amcattest.AmcatTestCase):
    
    def testTreeLabels(self):
        "Test that label caching works"
        self.db.beforeQueryListeners.add(lambda x : print(x))
        for tid in [5000]:
            t = Tree(self.db, tid)
            t.cacheLabels()
            with self.db.disabled():
                for o in t.getObjects():
                    y = o.label
    def testTreeConsistency(self):
        "Are all classes consistent and does caching work?"
        for tid in [100]:
            t = Tree(self.db, tid)
            #test_hierarchy.testConsistency(t)
            t.uncache()
            t.cacheHierarchy()
            with self.db.disabled():
                test_hierarchy.testConsistency(t)

    def testParent(self):
        "Test specific parents"
        for oid, tree, parent, reverse in test_object.PARENTS:
            t = Tree(self.db, tree)
            self.assertEqual(t.getParent(oid), t.getObject(parent))
            self.assertEqual(t.getObject(oid).parent, t.getObject(parent))
            self.assertEqual(t.isReversed(oid), reverse, "%r.%r reverse is %s should be %s" % (t, oid, t.isReversed(oid), reverse))

    


if __name__ == '__main__':
    amcattest.main()
