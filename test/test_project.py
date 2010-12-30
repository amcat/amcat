import dbtoolkit, unittest, project, article, user, mx.DateTime, datetime, amcattest

class TestProject(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB()#use_app=True)

    def tesxUsers(self):
        p = project.Project(self.db, 1)
        self.assertIn(user.User(self.db, 2), p.users)

    def testType(self):
        p = project.Project(self.db, 292)
        for (propname, types, card) in (
            ("sets", project.Set, True),
            ("articles", article.Article, True),
            ("users", user.User, True),
            ("name", unicode, None),
            ("insertDate", datetime.datetime, None),
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
