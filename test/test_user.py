from amcat.test import amcattest
from amcat.model import user, project, authorisation
from amcat.db import dbtoolkit

class TestUser(amcattest.AmcatTestCase):

    def setUp(self):
        super(TestUser, self).setUp()
        self.app = self.db.getUser()

    def testProperties(self):
        self.assertEqual(self.app.username, "app")
        self.assertEqual(self.app.fullname, "'nepaccount' voor applicatie")
        self.assertEqual(str(self.app.affiliation), "VU")

    def testUserProjects(self):
        for projectid in (1,2):
            self.assertIn(projectid, [p.id for p in self.app.projects])
        self.assertEqual(list(self.app.roles), [])

    def testCurrentUserIsAdmin(self):
        # this test will fail if ran by non-admins
        db = dbtoolkit.amcatDB()
        me = db.getUser()
        self.assertIn(authorisation.Role(db, 1), me.roles)
        
    def testCreateDelete(self):
        # this test will fail if ran by non-admins
        db = dbtoolkit.amcatDB()
        args = {"username" : "testCreateDelete_user2123",
                "password" : "4908sadf",
                "email" : "test@test.com",
                "fullname" : "Jolly Good",
                "active" : True,
                "affiliation" : 1}
        
        user.User.create(db, **args)
        self.db.commit()
        
        u = user.User.get(db, username=args['username'])
        for k,v in args.items():
            self.assertEqual(v, getattr(u, k))
            
        u.delete()
        
        self.assertRaises(ValueError, user.User.get(db, username=args['username']))

    def testTypes(self):
        self.assertEqual(user.User.projects.getType(), project.Project)
        self.assertTrue(user.User.projects.getCardinality())
        
        self.assertEqual(user.User.projectroles.getType(), (project.Project, authorisation.Role))
        self.assertSubclass(user.User.projectroles.getCardinality(), dict)
        

if __name__ == '__main__':
    amcattest.main()
