import amcattest, codingjob, dbtoolkit, cachable2

class TestProject(amcattest.AmcatTestCase):

    def setUp(self):
        self.db = dbtoolkit.amcatDB(use_app=True)

    def testObjects(self):
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
        
if __name__ == '__main__':
    amcattest.main()
