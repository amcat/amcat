import dbtoolkit, unittest, project, batch, user, mx.DateTime, datetime, amcattest

class TestProject(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testUsers(self):
        p = project.Project(self.db, 1)
        self.assertIn(user.User(self.db, 2), p.users)

    def testType(self):
        p = project.Project(self.db, 1)
        for (propname, types, card) in (
            ("batches", batch.Batch, True),
            ("users", user.User, True),
            ("name", str, None),
            ("insertDate", (mx.DateTime.DateTimeType, datetime.datetime), None),
            ):
            if type(types) not in (tuple, set, list): types = (types,)
            self.assertIn(p.getType(propname), types, "checking type(Project.%s)" % propname)
            prop = getattr(project.Project, propname)
            if card is True:
                self.assertTrue(prop.getCardinality())
            else:
                self.assertEqual(prop.getCardinality(), card)
        
        

if __name__ == '__main__':
    unittest.main()
