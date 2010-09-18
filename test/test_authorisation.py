import unittest, authorisation, dbtoolkit, inspect


class TestSentences(unittest.TestCase):
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

    def test_check(self):
        #Can only check 'app' and current user permissions...
        db2 = dbtoolkit.amcatDB()
        roleids = set(r.id for r in db2.getUser().roles)

        for (privilege, projectid, result) in (
            ("global_add_user",None,authorisation.AccessDenied),
            ):
            # check app roles (hardcoded)
            if inspect.isclass(result) and issubclass(result, Exception):
                self.assertRaises(result, authorisation.check, self.db, privilege, projectid)
            else:
                self.assertEqual(authorisation.check(self.db, privilege, projectid), result)

            # check user role (esp for admin superrole escalation, can't test that on app)
            neededrole = authorisation.getPrivilege(self.db, privilege).role.id
            if set([neededrole, 1]) & roleids:
                self.assertEqual(authorisation.check(db2, privilege, projectid), None)
            else:
                self.assertRaises(authorisation.AccessDenied, authorisation.check, db2, privilege, projectid)
        
                
if __name__ == '__main__':
    unittest.main()
