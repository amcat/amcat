import unittest, amcattest, authorisation, dbtoolkit, inspect, warnings
from authorisation import check, AccessDenied

class TestAuthorisation(amcattest.AmcatTestCase):
    def setUp(self):
        self.db = dbtoolkit.amcatDB(profile=True, use_app=True)
    
    def test_roles(self):
        for (input, output) in (
            (1, "admin"),
            ):
            r = authorisation.Role(self.db, input)
            self.assertEqual(r.label, output)

    def test_privileges(self):
        for (pid, label, roleid, projectlevel) in (
            (1, 'global_add_user', 2, False),
            (2, 'project_add_user', 2, True),
            ):
            p = authorisation.Privilege(self.db, pid)
            self.assertEqual(p.label, label)
            self.assertEqual(p.role.id, roleid)
            self.assertEqual(p.projectlevel, projectlevel)

    def test_getPrivilege(self):
        for (input, output) in (
            (1, 1),
            ("global_add_user", 1),
            ("global_add", ValueError),
            (authorisation.Privilege(self.db, 1), 1),
            ):
            if inspect.isclass(output) and issubclass(output, Exception):
                self.assertRaises(output, authorisation.getPrivilege, self.db, input)
            else:
                self.assertEqual(authorisation.getPrivilege(self.db, input).id, output)

    def test_check_global(self):
        # app should not have global_add_user priv
        self.assertRaises(AccessDenied, check, self.db, "global_add_user")
    def test_check_global_currentusersuperadmin(self):
        # assume that the currently logged in user has superadmin role
        me = dbtoolkit.amcatDB().getUser()
        if me.username not in ('wva',):
            warnings.warn(Warning("Current user is not a superadmin; skipping some tests"))
        self.assertNotRaises(check(me, "global_add_user"))
        self.assertNotRaises(check(me, "project_add_user", 2))
        self.assertNotRaises(check(me, "project_add_user", -1))

        
    def test_check_project(self):
        # cannot check project_add_user without project
        self.assertRaises(ValueError, check, self.db, "project_add_user")
        # app is admin on project 1 (so should escalate)
        self.assertNotRaises(check(self.db, "project_add_user", 1))
        # app is useradmin on project 2
        self.assertNotRaises(check(self.db, "project_add_user", 2))
        # app is nothing on project 3
        self.assertRaises(AccessDenied, check, self.db, "project_add_user", 3)
        
if __name__ == '__main__':
    unittest.main()
