import dbtoolkit, unittest, system

class TestSystem(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
        self.system = system.System(self.db)

    def test_singleton(self):
        self.assertTrue(self.system is system.System(self.db))

    def test_access(self):
        self.assertTrue(self.system.users)
        self.assertTrue(self.system.projects)
        self.assertTrue(self.system.analyses)

if __name__ == '__main__':
    unittest.main()
