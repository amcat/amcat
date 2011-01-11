from amcat.test import amcattest

from amcat.model.coding import codingjob, annotationschema
from amcat.tools import idlabel
from amcat.db import dbtoolkit


class TestAnnotationSchema(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testSchema(self):
        # check whether we can create objects without errors
        for (sid, name, table, articleschema) in [
            (0, "Leeg","net_arrows", False),
            (1, "iNetSchema","net_arrows", False),
            (3, "SimpleArticleAnnotation","articles_annotations", True),
            ]:
            
            a = annotationschema.AnnotationSchema(self.db, sid)
            self.assertEqual(a.name, name)
            self.assertEqual(a.table, table)
            #self.assertEqual(a.isarticleschema, articleschema)
            #DOES NOT WORK on old db, so disable for now

    def testFields(self):
        for (sid, fieldnames) in [
            (0, ['topic']),
            (1, ['source', 'subject', 'predicate', 'quality', 'arrowtype', 'object', 'angle']),
            (3, ['comments', 'irrelevant']),
            ]:
            # test field names
            a = annotationschema.AnnotationSchema(self.db, sid)
            fns = [f.fieldname for f in a.fields]
            self.assertEqual(fns, fieldnames)
            # test getFieldb
            for f, fn in zip(a.fields, fieldnames):
                f2 = a.getField(fn)
                self.assertEqual(f, f2)

    def testSerialisation(self):
        for (sid, fieldname, value, obj, lbl) in [
            (1, 'arrowtype', 4, idlabel.IDLabel(4, 'AFF'), 'AFF'),
            #TODO: (1, 'subject', 1000, ont.Object(self.db, 1000), 'ww (werkloosheidswet)'),
            (1, 'predicate', 'bla','bla','bla'),
            ]:
            a = annotationschema.AnnotationSchema(self.db, sid)
            f = a.getField(fieldname)
            val = f.deserialize(value)
            self.assertEqual(str(val), lbl)
            self.assertEqual(val, obj)

    
if __name__ == '__main__':
    amcattest.main()
