import dbtoolkit, unittest, system, amcattest

class TestSystem(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
        self.system = system.System(self.db)

    def test_singleton(self):
        self.assertTrue(self.system == system.System(self.db))

    def test_access(self):
        self.assertNotEmpty(self.system.users)
        self.assertNotEmpty(self.system.roles)
        self.assertNotEmpty(self.system.privileges)
        self.assertNotEmpty(self.system.projects)
        self.assertNotEmpty(self.system.analyses)
        
        user = self.system.getUserByUsername('wva')
        self.assertTrue(user.username == 'wva')
        

if __name__ == '__main__':
    unittest.main()
