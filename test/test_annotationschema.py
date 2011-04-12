from amcat.test import amcattest

from amcat.model.coding import codingjob, annotationschema
from amcat.tools import idlabel
from amcat.db import dbtoolkit


class TestAnnotationSchema(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)



    def testFields(self):
        for (sid, fieldnames) in [
            (0, ['topic']),
            (1, ['source', 'subject', 'predicate', 'quality', 'arrowtype', 'object', 'angle']),
            (3, ['comments', 'irrelevant']),
            ]:
            # test field names
            a = annotationschema.AnnotationSchema(self.db, sid)
	    fields = list(a.fields)
            fns = [f.fieldname for f in fields]
            self.assertEqual(fns, fieldnames)
            # test getFieldb
            for f, fn in zip(a.fields, fieldnames):
                f2 = a.getField(fn)
                self.assertEqual(f, f2)

    def testSchema(self):
        # check whether we can create objects without errors
        for (sid, name, table, articleschema) in [
            (0, "Leeg","vw_net_arrows", False),
            (1, "iNetSchema","vw_net_arrows", False),
            (3, "SimpleArticleAnnotation","articles_annotations", True),
            ]:
            
            a = annotationschema.AnnotationSchema(self.db, sid)
            self.assertEqual(a.name, name)
            self.assertEqual(a.table, table)
            self.assertEqual(a.isarticleschema, articleschema)
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


    def testValidateField(self):
        for (sid,fieldname, value, err) in [
            (1, 'predicate', None, None),
            (87, 'topic', None, annotationschema.ValidationError),
            ]:
            a = annotationschema.AnnotationSchema(self.db, sid)
            f = a.getField(fieldname)
            o = f.deserialize(value)
            if err:
                self.assertRaises(err, f.validate, o)
            else:
                f.validate(o)

    def testValidateSchema(self):
        for (sid, values, err) in [
            (1, {}, None),
            (87, {}, annotationschema.ValidationError),
            (87, {"to":1, "topic":-1234},None),
            ]:
            a = annotationschema.AnnotationSchema(self.db, sid)
            objects = a.deserializeValues(**values)
            if err:
                self.assertRaises(err, a.validate, objects)
            else:
                a.validate(objects)
            
    
if __name__ == '__main__':
    amcattest.main()
