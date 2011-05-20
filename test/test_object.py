from amcat.model.ontology.object import Object
from amcat.model.ontology.tree import Tree

from amcat.model.language import Language
from amcat.test import amcattest

import datetime

PARENTS = ( # objectid, treeid, parentid/None, reverse?
    (307, 100, None, False),
    (14409, 100, 2547, False),
    (587, 6000, 2231, True),
    )



class TestObject(amcattest.AmcatTestCase):    

    def testSearchString(self):
	o = Object(self.db, 698)
	self.assertEqual(o.getSearchString(languageid=13), "")

class Stop:

    def testLabels(self):
        for oid, stdlabel, lang, label in (
            (296, "flexibele arbeidsmarkt", 12, "[-] Flexibele / Liberale arbeidsmarkt"),
            ):
            o = Object(self.db, oid)
            self.assertEqual(str(o.label), stdlabel)
            self.assertEqual(str(o.labels[Language(self.db, lang)]), label)
            self.assertEqual(str(o.getLabel(lang)), label)
            self.assertRaises(KeyError, lambda  : o.labels[-99])
            self.assertEqual(o.getLabel(-99), stdlabel)
    def testParent(self):
        for oid, treeid, parentid, reverse in PARENTS:
            o = Object(self.db, oid)
            if parentid is None:
                self.assertEqual(o.getParent(treeid), None)
            else:
                self.assertEqual(o.getParent(treeid).id, parentid)
            self.assertIn(Tree(self.db, treeid), o.trees)
    
    def testFunctions(self):
        verdonk = Object(self.db, 1731)
        
        for date, nfunctions, searchstring in (
            (datetime.datetime(2001,1,1), 1, 'Verdonk AND (Rita^0 OR vvd "Volkspartij Vrijheid Democratie"~5^0)'),
            (datetime.datetime(2004,1,1), 2, 'Verdonk AND (Rita^0 OR vvd "Volkspartij Vrijheid Democratie"~5^0 OR "ministerie justitie"~5^0 OR bewinds*^0 OR staatssecret*^0)'),
            (datetime.datetime(2007,1,1), 3,'Verdonk AND (Rita^0 OR vvd "Volkspartij Vrijheid Democratie"~5^0 OR "tweede kamerlid" "tweede kamerleden" kamerlid kamerleden^0 OR parlement*^0 OR "tweede kamer*"^0 OR "ministerie justitie"~5^0 OR bewinds*^0 OR minister*^0)'),
            (datetime.datetime(2009,1,1), 2,'Verdonk AND (Rita^0 OR "trots op nederland" (TON AND verdonk)^0 OR "tweede kamerlid" "tweede kamerleden" kamerlid kamerleden^0 OR parlement*^0 OR "tweede kamer*"^0)'),
            ):
            self.assertEqual(nfunctions, len(list(verdonk.currentFunctions(date))))
            #self.assertEqual(searchstring, verdonk.getSearchString(date))
            


if __name__ == '__main__': amcattest.main()
