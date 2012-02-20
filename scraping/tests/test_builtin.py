import datetime
import unittest
import types
import json
import io

from amcat.tools.scraping.objects import Document
from amcat.tools.scraping.exporters.builtin import Exporter, JSONExporter

class ExporterTest(unittest.TestCase):
    def test_id(self):
        exp = Exporter()
        for i in range(100000):
            self.assertEqual(i, next(exp.id))

        self.assertEqual(types.GeneratorType, type(exp.id))

    def test_already_closed(self):
        exp = JSONExporter(io.StringIO())

        self.assertEqual(False, exp.closed)

        exp.close()

        self.assertEqual(True, exp.closed)
        self.assertRaises(IOError, exp.close)
        self.assertRaises(IOError, lambda:exp.commit(None))

class JSONExporterTest(ExporterTest):
    def test_init(self):
        fo = io.StringIO()
        exp = JSONExporter(fo)

    def test_close_io(self):
        fo = io.StringIO()
        exp = JSONExporter(fo)

        fo.seek(0)
        self.assertEqual(fo.read().strip('\n'), '[')

        exp.close()
        self.assertRaises(ValueError, lambda:fo.read())

    def test_close(self):
        fo = io.StringIO()
        exp = JSONExporter(fo, close_io=False)
        exp.close()

        fo.read()

    def test_subset(self):
        fo = io.StringIO()
        exp = JSONExporter(fo, close_io=False)

        doc = Document()
        doc.updateprops({
          'string' : 'test',
          'boolean' : True,
          'null' : None,
          'datetime' : datetime.datetime(2010, 5, 5, 5, 5),
          'date' : datetime.date(2010, 5, 5),
          'integer' : 5,
          'float' : 5.5,
          'unicode' : 'éééà'
        })

        props = doc.getprops()

        exp.commit(doc)
        exp.commit(doc) # The same document shouldn't be committed twice
        exp.close()

        fo.seek(0)
        jprops = json.load(fo)
        self.assertEqual(len(jprops), 1)

        jprops = jprops[0]
        for k,v in props.items():
            self.assertTrue(k in jprops)

            if type(v) in (datetime.datetime, datetime.date):
                self.assertEqual(str(v), jprops[k])
            else:
                self.assertEqual(v, jprops[k])

if __name__ == '__main__':
    unittest.main()
