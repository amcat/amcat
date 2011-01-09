from amcat.test import amcattest, test_hierarchy, test_object
from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree


class TestTree(amcattest.AmcatTestCase):
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
            self.assertEqual(t.isReversed(oid), reverse)


if __name__ == '__main__':
    amcattest.main()
