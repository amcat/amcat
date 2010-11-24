import externalscripts, amcattest, dbtoolkit

class ExternalScriptTest(amcattest.AmcatTestCase):
    
    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)
        
    def testGetScript(self):
        es = externalscripts.getScript(self.db, 1)
        import scripts.testscript
        self.assertEqual(type(es), scripts.testscript.TestScript)

    def testInvocation(self):
        inv = externalscripts.Invocation(self.db, 1)
        es = externalscripts.getScript(self.db, 1)
        self.assertEqual(type(inv.getScript()), type(es))

        self.assertRaises(Exception, inv.getProgress().isDone)
        
        

if __name__ == '__main__':
    amcattest.main()
