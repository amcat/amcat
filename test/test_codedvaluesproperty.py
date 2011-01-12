from amcat.test import amcattest
from amcat.tools.cachable import codedvaluesproperty, cachable, cacher
from amcat.model.coding import annotationschema

from amcat.model.ontology.object import Object

class TestCVP(cachable.Cachable):

    def __init__(self, db, id, schemaid):
	cachable.Cachable.__init__(self, db, id)
	self.schemaid = schemaid
    
    @property
    def label(self):
	return "X"

    def getSchema(self):
	return annotationschema.AnnotationSchema(self.db, self.schemaid)	
    
    values = codedvaluesproperty.CodedValuesProperty(getSchema)
    

class CVPTest(amcattest.AmcatTestCase):
    
    def testget(self):
        rid, subjid, pred, atype, qual = self.db.doQuery("select top 1 arrowid, subject, predicate, arrowtype, quality from net_arrows")[0]
	atypelbl = self.db.getValue("SELECT [name] FROM [net_arrowtypes] where arrowtypeid=%i" % atype) 

	c = TestCVP(self.db, rid, 72)
        v = c.values

        self.assertEqual(pred,v.predicate)
        self.assertEqual(qual,v.quality)
        self.assertEqual(Object(self.db,subjid),v.subject)
	self.assertEqual(atypelbl,str(v.arrowtype))

    def testcache(self):
        data = self.db.doQuery("select top 10 arrowid, subject, quality from net_arrows")
	objs = [TestCVP(self.db, r[0], 72) for r in data]

	cacher.cache(objs, "values")

	for obj, (rid, subj, qual) in zip(objs, data):
	    v = obj.values
	    self.assertEqual(obj.values.subject.id, subj)
	    self.assertEqual(obj.values.quality, qual)

    def testcachedifferent(self):
        data1 = self.db.doQuery("select top 10 arrowid, subject, quality from net_arrows")
	objs1 = [TestCVP(self.db, r[0], 72) for r in data1]

	data2 = self.db.doQuery("select top 10 codingjob_articleid, topic from antwerpen_articles_annotations")
	objs2 = [TestCVP(self.db, r[0], 68) for r in data2]

	self.db.startProfiling()
	cacher.cache(objs1+objs2, "values")
	self.db.printProfile()
	
	for obj, (rid, subj, qual) in zip(objs1, data1):
	    self.assertEqual(obj.values.subject.id, subj)
	    self.assertEqual(obj.values.quality, qual)

	for obj, (rid, topic) in zip(objs2, data2):
	    self.assertEqual(obj.values.topic.id, topic)
	self.db.printProfile()



if __name__ == '__main__':
    amcattest.main()
