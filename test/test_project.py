import dbtoolkit, unittest, project, batch, user, mx.DateTime

class TestProject(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testUsers(self):
        p = project.Project(self.db, 1)
        self.assertTrue([u for u in p.users if u.id == 2])

    def testType(self):
        p = project.Project(self.db, 1)
        for (prop, type, card) in (
            ("batches", batch.Batch, list),
            ("users", user.User, list),
            ("name", str, None),
            ("insertDate", mx.DateTime.DateTimeType, None),
            ):
            self.assertEqual(p.getType(prop), type)
            self.assertEqual(p.getCardinality(prop), card)
        
        

if __name__ == '__main__':
    unittest.main()
