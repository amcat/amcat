import amcattest, codingjob, dbtoolkit, cachable2

class TestProject(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def xtestObjects(self):
        # check whether we can create objects without errors
        for cjid in [5175]:
            cj = codingjob.Codingjob(self.db, cjid)
            unitschema, artschema = cj.unitSchema, cj.articleSchema
            for schema in unitschema, artschema:
                print schema.id
                print schema.label
                schema.table
                list(schema.fields)            
            for cjset in cj.sets:
                arts = list(cjset.articles)
        
    def xtestCache(self):
        c = codingjob.Codingjob(self.db, 5175)
        cachable2.cache(c, **{'sets': {'articles' : {'article' : {'source' : ["name"]}}}})

    def testSimpleCodedSentence(self):
        #test an article with net codings
        cjaid = 16284
        arrowid = 30188
        ca = codingjob.CodedArticle(self.db, cjaid)
        s = list(ca.sentences)[0]
        
    def testCodedArticle(self):
        # test an article with agenda codings
        cjaid = 1609147
        ca = codingjob.CodedArticle(self.db, cjaid)
        self.assertEqual(ca.article.id, 45833360)
        self.assertEqual(ca.article.headline, 'Matiging')
        self.assertEqual(ca.set.job.id, 5175)
        self.assertEqual(ca.set.setnr, 1)
        self.assertEqual(ca.annotationschema.id, 26)
        self.assertEqual(ca.getValue("topic").id, 10490)
        self.assertEqual(ca.topic.id, 10490)
        self.assertEqual(list(ca.sentences), [])

    def testCodedSentence(self):
        #test an article with net codings
        cjaid = 16284
        arrowid = 30188
        ca = codingjob.CodedArticle(self.db, cjaid)
        self.assertEqual(ca.article.id, 33379889)
        self.assertNotEmpty(list(ca.sentences))
        self.assertIn(30188, [cs.id for cs in ca.sentences])
        cs = [cs for cs in ca.sentences if cs.id == 30188][0]
        self.assertEqual(cs.getValue("object").id, 1625)
        self.assertEqual(cs.subject.id, 1098)
        self.assertEqual(cs.predicate, 'idealistisch, niet de hele dag')

    def testCodingJob(self):
        # test basic properties
        cj = codingjob.CodingJob(self.db, 5175)
        self.assertEqual(cj.name, "De Standaard (1984 - sample)")
        self.assertEqual(cj.articleSchema.id, 26)
        self.assertEqual(cj.unitSchema.id, 0)
        self.assertEqual(cj.owner.username, 'anneh')
        
    def testCodingJobToArticle(self):
        # can we get to an article from the coding job?
        cj = codingjob.CodingJob(self.db, 5175)
        self.assertIn(1, [s.setnr for s in cj.sets])
        s = [s for s in cj.sets if s.setnr == 1][0]
        self.assertIn(codingjob.CodedArticle(self.db, 1609147), s.articles)
        self.assertEqual(cj.articleSchema, codingjob.CodedArticle(self.db, 1609147).annotationschema)
           
        
        
        
if __name__ == '__main__':
    amcattest.main()
