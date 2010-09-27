import dbtoolkit, unittest, user, system, authorisation, project, types, amcattest

class TestUser(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
        self.app = self.db.getUser()

    def testProperties(self):
        self.assertEqual(self.app.username, "app")
        self.assertEqual(self.app.fullname, "'nepaccount' voor applicatie")
        self.assertEqual(self.app.affiliation, "VU")

    def testUserProjects(self):
        for projectid in (1,2):
            self.assertIn(projectid, [p.id for p in self.app.projects])
        self.assertEqual(list(self.app.roles), [])

    def testCurrentUserIsAdmin(self):
        # this test will fail if ran by non-admins
        db = dbtoolkit.amcatDB()
        me = db.getUser()
        self.assertIn(authorisation.Role(db, 1), me.roles)

    def testTypes(self):
        self.assertEqual(user.User.projects.getType(), project.Project)
        self.assertTrue(user.User.projects.getCardinality())
        
        self.assertEqual(user.User.projectroles.getType(), (project.Project, authorisation.Role))
        self.assertSubclass(user.User.projectroles.getCardinality(), dict)
        
    def testDeprecated(self):
        db = dbtoolkit.amcatDB()
        me = db.getUser()
        self.assertTrue(me.isSuperAdmin)
        self.assertTrue(me.canViewAllProjects)
        self.assertFalse(me.canCreateNewProject)
        
        app = self.db.getUser()
        self.assertFalse(app.isSuperAdmin)
        self.assertFalse(app.canViewAllProjects)
        self.assertFalse(app.canCreateNewProject)

        for d in (db, self.db):
            self.assertEqual(user.currentUser(d), d.getUser())
            self.assertEqual(list(user.users(d)), list(system.System(d).users))

if __name__ == '__main__':
    unittest.main()
