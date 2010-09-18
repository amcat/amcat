import unittest, authorisation, dbtoolkit


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

        
if __name__ == '__main__':
    unittest.main()
