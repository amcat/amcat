import dbtoolkit, unittest, project, batch, user, mx.DateTime, datetime

class TestProject(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testUsers(self):
        p = project.Project(self.db, 1)
        self.assertTrue([u for u in p.users if u.id == 2])

    def testType(self):
        p = project.Project(self.db, 1)
        for (prop, types, card) in (
            ("batches", batch.Batch, list),
            ("users", user.User, list),
            ("name", str, None),
            ("insertDate", (mx.DateTime.DateTimeType, datetime.datetime), None),
            ):
            if type(types) not in (tuple, set, list): types = (types,)
            self.assertTrue(p.getType(prop) in types)
            self.assertEqual(p.getCardinality(prop), card)
        
        

if __name__ == '__main__':
    unittest.main()
