import unittest
import re
import rdflib
import os

from fuseki import Fuseki
from pysoh import SOHServer

import logging
log = logging.getLogger(__name__)


TEST_PORT = 9876

FIXTURE = '''@prefix : <http://example.org/#> .
             []   :says  "Hello World"'''

def get_test_soh():
    soh_port = os.environ.get('SOH_TEST_SERVER')
    if soh_port:
        return SOHServer(soh_port)
    else:
        return Fuseki(port=TEST_PORT)
    

class TestSOH(unittest.TestCase):

    #TODO: Do something useful if fuseki is not installed
    
    def setUp(self):
        try:
            self.soh = get_test_soh()
        except OSError:
            log.exception("Cannot find fuseki")
            return
        self.soh.prefixes[""] = "http://example.org/#"
        self.soh.add_triples(FIXTURE, clear=True)


    def tearDown(self):
        try:
            del self.soh
        except AttributeError:
            pass
        except:
            log.exception("Error on clearing SOH")

    def assertGraphContains(self, graph, pattern):
        nt = graph.serialize(format='nt')
        m = re.search(pattern, nt, re.M)
        self.assertTrue(m, "Graph did not match pattern {pattern!r}:\n{nt}".format(**locals()))

    def test_query(self):
        return
        result = self.soh.do_query("SELECT ?x ?z WHERE {?x ?y ?z}")
        self.assertEqual(list(result), [['_:b0', 'Hello World']])

    def todo_test_add_triples_rdf(self):
        """Can we add rdf triples from an rdflib graph"""
        g = rdflib.Graph()
        ex = rdflib.Namespace("http://example.org/")
        g.add((ex["John"], ex["loves"], rdflib.Literal("Mary")))
        self.soh.add_triples(g, clear=True)
        g = self.soh.get_triples()
        self.assertEqual(len(g), 1)
        self.assertGraphContains(g,r'<http://example.org/John> <http://example.org/loves> "Mary" .')

    def todo_test_get(self):
        """Can we get the fixture triples?"""
        g = self.soh.get_triples()
        self.assertEqual(len(g), 1)
        self.assertGraphContains(g, r'^_:\w+ <http://example.org/#says> "Hello World" .')

    def todo_test_do_update(self):
        """Can we update triples?"""
        self.soh.do_update('''PREFIX : <http://example.org/#>
                           INSERT { ?x :istalking "True" }
                           WHERE  { ?x :says ?y}''')
        g = self.soh.get_triples()
        self.assertEqual(len(g), 2)
        self.assertGraphContains(g, r'^_:\w+ <http://example.org/#istalking> "True" .')

    def todo_test_update(self):
        """Can we update triples with the higher level update command?"""
        self.soh.update("?x :says ?y", "?x :istalking 'True'")
        g = self.soh.get_triples()
        self.assertEqual(len(g), 2)
        self.assertGraphContains(g, r'^_:\w+ <http://example.org/#istalking> "True" .')



if __name__ == '__main__':
    unittest.main()
