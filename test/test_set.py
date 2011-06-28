from amcat.model.set import Set
from amcat.model import project, user
from amcat.test import amcattest

class TestSet(amcattest.AmcatTestCase):

    def testSet(self):
        for (setid, projectid, name, ownerid) in (
            (1562, 258, "aswolk 2010", 86),
            ):
            s = Set(self.db, setid)
            self.assertEqual(s.project, project.Project(self.db, projectid))
            self.assertEqual(s.owner.id, ownerid)
            self.assertEqual(str(s), name)
            self.assertTrue(list(s.articles))

        
        

if __name__ == '__main__':
    amcattest.main()
