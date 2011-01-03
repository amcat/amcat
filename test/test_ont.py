#import amcattest, ont, language, datetime
from amcat.test import amcattest


def Hide():
  class TestOntology(amcattest.AmcatTestCase):    

    def testLabels(self):
        for oid, stdlabel, lang, label in (
            (296, "flexibele arbeidsmarkt", 12, "[-] Flexibele / Liberale arbeidsmarkt"),
            ):
            o = ont.Object(self.db, oid)
            self.assertEqual(o.label, stdlabel)
            self.assertEqual(o.labels[language.Language(self.db, lang)], label)
            self.assertEqual(o.getLabel(lang), label)
            self.assertRaises(KeyError, lambda  : o.labels[-99])
            self.assertEqual(o.getLabel(-99), None)

    def testFunctions(self):
        verdonk = ont.Object(self.db, 1731)
        
        for date, nfunctions, searchstring in (
            (datetime.datetime(2001,1,1), 1, 'Verdonk AND (Rita^0 OR vvd "Volkspartij Vrijheid Democratie"~5^0)'),
            (datetime.datetime(2004,1,1), 2, 'Verdonk AND (Rita^0 OR vvd "Volkspartij Vrijheid Democratie"~5^0 OR "ministerie justitie"~5^0 OR bewinds*^0 OR staatssecret*^0)'),
            (datetime.datetime(2007,1,1), 3,'Verdonk AND (Rita^0 OR vvd "Volkspartij Vrijheid Democratie"~5^0 OR "tweede kamerlid" "tweede kamerleden" kamerlid kamerleden^0 OR parlement*^0 OR "tweede kamer*"^0 OR "ministerie justitie"~5^0 OR bewinds*^0 OR minister*^0)'),
            (datetime.datetime(2009,1,1), 2,'Verdonk AND (Rita^0 OR "trots op nederland" (TON AND verdonk)^0 OR "tweede kamerlid" "tweede kamerleden" kamerlid kamerleden^0 OR parlement*^0 OR "tweede kamer*"^0)'),
            ):
            self.assertEqual(nfunctions, len(list(verdonk.currentFunctions(date))))
            self.assertEqual(searchstring, verdonk.getSearchString(date))
            
            
    def testClassHierarchy(self):
        for oid, parents, children in (
            (1731, {4003 : None, 9999 : False}, {}),
            #(1646, None),
            (10276, {9999: 10275, 4003 : False}, {}),
            #(10275, {9999: None}, {}),

            ):
            o = ont.Object(self.db, oid)
            parentiddict = dict((cl.id, p and p.id) for (cl, p) in o.parents.items())
            for cl, parent in parents.iteritems():
                if parent is False:
                    self.assertNotIn(cl, parentiddict.keys())
                else:
                    self.assertIn(cl, parentiddict.keys())
                    self.assertEqual(parent, parentiddict[cl])

            #childiddict = dict((cl.id, set(c.id for c in cc)) for (cl,cc) in o.children.items())

    def testCategorisation(self):
        c = ont.Set(self.db, 5001)
        o = ont.Object(self.db, 1560)
        self.assertEqual([o2.id for o2 in c.getCategorisationPath(o)], [366, 10661])
        self.assertEqual(c.categorise(o, depth=[1])[0].id, 366)
        #self.assertEqual(c.categorise(o, depth=[1], returnOmklap=True, returnObjects=False)[0], 1)
        # dim cosmo?
                    
    #TODO: sets, sethierarchy, classes, boundobjects, categorizations

        
        


if __name__ == '__main__': amcattest.main()
