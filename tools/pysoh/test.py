import unittest
import re
import rdflib

from fuseki import Fuseki

TEST_PORT = 9876

FIXTURE = '''@prefix : <http://example.org/#> .
             []   :says  "Hello World"'''

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        self.soh = Fuseki(port=TEST_PORT)
        self.soh.add_triples(FIXTURE)

    def tearDown(self):
        del self.soh

    def assertGraphContains(self, graph, pattern):
        nt = graph.serialize(format='nt')
        m = re.search(pattern, nt, re.M)
        self.assertTrue(m, "Graph did not match pattern {pattern!r}:\n{nt}".format(**locals()))

    def test_query(self):
        result = self.soh.query("SELECT ?x ?z WHERE {?x ?y ?z}")
        self.assertEqual(list(result), [['_:b0', 'Hello World']])
    
class Stop:
        
    def test_add_triples_rdf(self):
        """Can we add rdf triples from an rdflib graph"""
        g = rdflib.Graph()
        ex = rdflib.Namespace("http://example.org/")
        g.add((ex["John"], ex["loves"], rdflib.Literal("Mary")))
        self.soh.add_triples(g, clear=True)
        g = self.soh.get_triples()
        self.assertEqual(len(g), 1)
        self.assertGraphContains(g,r'<http://example.org/John> <http://example.org/loves> "Mary" .')

    def test_get(self):
        """Can we get the fixture triples?"""
        g = self.soh.get_triples()
        self.assertEqual(len(g), 1)
        self.assertGraphContains(g, r'^_:\w+ <http://example.org/#says> "Hello World" .')

    def test_update(self):
        """Can we update triples?"""
        self.soh.update('''PREFIX : <http://example.org/#>
                           INSERT { ?x :istalking "True" }
                           WHERE  { ?x :says ?y}''')
        g = self.soh.get_triples()
        self.assertEqual(len(g), 2)
        self.assertGraphContains(g, r'^_:\w+ <http://example.org/#istalking> "True" .')



if __name__ == '__main__':
    unittest.main()
