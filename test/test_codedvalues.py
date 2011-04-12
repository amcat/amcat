from amcat.test import amcattest

from amcat.model.coding import codedvalues, codedarticle, codedsentence, annotationschema
from amcat.tools import idlabel
from amcat.db import dbtoolkit


class TestCodedValues(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def tearDown(self):
        self.db.rollback()
        
    def testUpdateArticleCoding(self):
        ca = codedarticle.CodedArticle(self.db, 1859186)
        s = ca.annotationschema
        ca.updateValues(self.db, {s.getField("comments") : "bla"})
        self.assertEqual(ca.values.comments, "bla")
        viasql = self.db.getValue("select comments from %s where codingjob_articleid = %i" % (s.table, ca.id))
        self.assertEqual(viasql, "bla")
                           


    def testUpdateNewArticleCoding(self):
        ca = codedarticle.CodedArticle(self.db, 1862599)
        self.assertEqual(ca.values, None)
        try:
            vals = ca.annotationschema.deserializeValues(politiek=True)
            ca.updateValues(self.db, vals)
            self.assertNotEqual(ca.values, None)
            self.assertEqual(ca.values.politiek, True)
        finally:
            self.db.rollback()
            del ca.values
        self.assertEqual(ca.values, None)
        
    def testUpdateValidation(self):
        cs = codedsentence.CodedSentence(self.db, 684712)
        self.assertRaises(annotationschema.ValidationError, cs.updateValues, self.db, {})
        ca = codedarticle.CodedArticle(self.db, 1862599)
        self.assertRaises(annotationschema.ValidationError, ca.updateValues, self.db, {})
        
            
    def testUpdateSentenceCoding(self):
        cs = codedsentence.CodedSentence(self.db, 684712)
        
        vals = cs.annotationschema.deserializeValues(subject=-1234, quality="1", object=-1234)

        self.assertNotEqual(cs.values.subject.id, -1234)
        try:
            cs.updateValues(self.db, vals)
            self.assertEqual(cs.values.subject.id, -1234)
            viasql = self.db.getValue("select subject from net_arrows where arrowid = %i" % cs.id)
            self.assertEqual(viasql, -1234)
        finally:
            self.db.rollback()
            del cs.values
        self.assertNotEqual(cs.values.subject.id, -1234)

    def testDeleteSentenceCoding(self):
        cs = codedsentence.CodedSentence(self.db, 684712)
        ca = cs.ca
        try:
            cs.delete(self.db)
            viasql = self.db.getValue("select arrowid from net_arrows where arrowid = %i" % cs.id)
            self.assertEqual(viasql, None)
            sids = [s.id for s in ca.sentences]
            self.assertNotIn(cs.id, sids)
        finally:
            self.db.rollback()
            del ca.sentences
            del cs.codedarticle
        
        

        
if __name__ == '__main__':
    amcattest.main()
