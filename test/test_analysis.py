import unittest, dbtoolkit, analysis
from amcattest import AmcatTestCase

class AnalysisTest(AmcatTestCase):
    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testAnalysis(self):
        a = analysis.Analysis(self.db, 2)
        self.assertEqual(a.label, "Alpino")
        self.assertEqual(a.language.id, 2)

if __name__ == '__main__':
    unittest.main()

