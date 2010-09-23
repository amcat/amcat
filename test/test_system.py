import dbtoolkit, unittest, system

class TestSystem(unittest.TestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
        self.system = system.System(self.db)

    def test_singleton(self):
        self.assertTrue(self.system == system.System(self.db))

    def test_access(self):
        self.assertTrue(self.system.users)
        self.assertTrue(self.system.roles)
        self.assertTrue(self.system.privileges)
        self.assertTrue(self.system.projects)
        self.assertTrue(self.system.analyses)
        self.assertTrue(self.system.annotationschemas)
        self.assertTrue(self.system.annotationschemafieldtypes)
        

if __name__ == '__main__':
    unittest.main()
