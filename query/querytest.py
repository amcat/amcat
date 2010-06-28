import unittest
import enginebase
import sys
import StringIO
import toolkit
import table3
import datetime
from idlabel import IDLabel
import cachingwrapper
import types

def debug(s):
    toolkit.ticker.warn(s)
    

class ListTestCase(unittest.TestCase):
    def __init__(self, testid, name, engine, concepts, filters, sortfields=None, limit=None, offset=None, distinct=False, check=None):
        self.testid = testid
        self.name = name
        self.engine = engine
        self.concepts = concepts
        self.filters = filters
        self.sortfields = sortfields
        self.limit = limit
        self.offset = offset
        self.distinct = distinct
        self.check = check
        self.lastresult = None
        unittest.TestCase.__init__(self)

    def runTest(self):
        debug("Running %s" % (self.shortDescription()))
        l = self.engine.getList(self.concepts, self.filters, self.sortfields, self.limit, self.offset, self.distinct)
        self.assertTrue(l)
        debug("Got list of size %ix%i" % (len(l.getRows()), len(l.getColumns())))
        self.assertTrue(l.getRows())
        self.assertTrue(l.getColumns())
        if self.check:
            self.assertTrue(self.check(l))
        self.lastresult = l

    def id(self):
        return self.testid

    def shortDescription(self):
        return "List %s:%s" % (self.testid, self.name)

        
class TableTestCase(unittest.TestCase):
    def __init__(self, testid, name, engine, rows, columns, cellagr, filters=None):
        self.testid = testid
        self.name = name
        self.engine = engine
        self.rows = rows
        self.columns = columns
        self.cellagr = cellagr
        self.filters = filters
        self.lastresult = None
        unittest.TestCase.__init__(self)

    def runTest(self):
        debug("Running %s" % (self.shortDescription()))
        t = self.engine.getTable(self.rows, self.columns, self.cellagr, self.filters)
        self.assertTrue(t)
        debug("Got table of size %ix%i" % (len(t.getRows()), len(t.getColumns())))
        self.assertTrue(t.getRows())
        self.assertTrue(t.getColumns())
        #import tableoutput; print tableoutput.table2unicode(t)
        self.lastresult = t
        
    def id(self):
        return self.testid
    def shortDescription(self):
        return "Table %s:%s" % (self.testid, self.name)
    
class QuoteTestCase(unittest.TestCase):
    def __init__(self, testid, name, engine, aid, quote):
        self.testid = testid
        self.name = name
        self.engine = engine
        self.aid = aid
        self.quote = quote
        self.lastresult = None
        unittest.TestCase.__init__(self)
    def runTest(self):
        debug("Running %s" % (self.shortDescription()))
        q = self.engine.getQuote(self.aid, self.quote)
        self.assertTrue(q)
        print "QUOTE:", q
        self.lastresult = q
    def id(self):
        return self.testid
    def shortDescription(self):
        return "Table %s:%s" % (self.testid, self.name)

class EqualResultCase(unittest.TestCase):
    def __init__(self, cases):
        unittest.TestCase.__init__(self)
        self.cases = cases
    def runTest(self):
        if len(self.cases) <= 1: return 
        objs = [c.lastresult for c in self.cases]
        for o in objs:
            for o2 in objs:
                if o is o2: continue
                if type(o) in (str, unicode, types.NoneType) or type(o2) in (str, unicode, types.NoneType):
                    self.assertEqual(o, o2) # quotes
                else:
                    self.equalTables(o, o2)
    def id(self):
        return "EqualResult(%s %s)" % (self.cases[0].id(), [c.engine for c in self.cases])
    def equalTables(self, t1, t2):
        def tocanonic(a):
            if type(a) == datetime.datetime: a = a.date()
            if type(a) in (list, tuple): a = tuple(tocanonic(x) for x in a)
            return a
        def isequal(a,b):
            a,b = map(tocanonic, (a,b))
            if a == b: return True
            if isinstance(a, IDLabel) and isinstance(b, IDLabel): return a.id == b.id
            if type(a) in (list, tuple) and type(b) in (list, tuple): return all(isequal(a2,b2) for (a2,b2) in zip(a,b))
            return False
        def checklists(l1, l2, name="lists"):
            self.assertTrue(isequal(len(l1), len(l2)), "%s not of equal size (%i <> %i)" % (name, len(l1), len(l2)))
            for i, (e1, e2) in enumerate(zip(l1, l2)):
                self.assertTrue(isequal(e1, e2), "%s element %i not equal (%s <> %s)" % (name, i, e1, e2))
        #import tableoutput;toolkit.warn("%s\n\n%s" % tuple(map(tableoutput.table2unicode, (t1, t2))))
        c1 = t1.getColumns()
        c2 = t2.getColumns()
        checklists(c1, c2, "Columns")
        r1 = t1.getRows()
        r2 = t2.getRows()
        checklists(r1, r2, "Rows")
        for col1, col2 in zip(c1, c2):
            for row1, row2 in zip(r1, r2):
                v1, v2 = t1.getValue(row1, col1), t2.getValue(row2, col2)
                self.assertTrue(isequal(v1, v2), "Value [%s x %s] not equal: %s <> %s" % (row1, col1, v1, v2))
        
    
    

class TestDescriptor(object):
    def __init__(self, testid, name, type, *args, **kargs):
        self.testid, self.name, self.type, self.args, self.kargs = testid, name, type, args, kargs
    def getTestCase(self, engine):
        if self.type == "list":
            return ListTestCase(self.testid, self.name, engine, *self.args, **self.kargs)
        elif self.type == "table":
            return TableTestCase(self.testid, self.name, engine, *self.args, **self.kargs)
        elif self.type == "quote":
            return QuoteTestCase(self.testid, self.name, engine, *self.args, **self.kargs)
        else: raise Exception("Unknown test type: %s" % self.type)
def Table(testid, name, *args, **kargs):
    return TestDescriptor(testid, name, "table", *args, **kargs)
def List(testid, name, *args, **kargs):
    return TestDescriptor(testid, name, "list", *args, **kargs)
def Quote(testid, name, *args, **kargs):
    return TestDescriptor(testid, name, "quote", *args, **kargs)

def getSuite(engines, descriptors):
    if isinstance(engines, enginebase.QueryEngineBase): engines = [engines]
    if isinstance(descriptors, TestDescriptor):  descriptors = [descriptors]

    suite = unittest.TestSuite()
    for descriptor in descriptors:
        cases = []
        for engine in engines:
            case = descriptor.getTestCase(engine)
            cases.append(case)
            suite.addTest(case)
        suite.addTest(EqualResultCase(cases))
    return suite

TITLE = "Test Report"
DESCRIPTION = "Test Report below:"
def runTests(engines, descriptors, html=False, title=TITLE, description=DESCRIPTION):
    suite = getSuite(engines, descriptors)
    output = StringIO.StringIO()
    
    if html:
        import HTMLTestRunner
        runner = HTMLTestRunner.HTMLTestRunner(
            stream=output, title=title, description = description)
    else:
        runner = unittest.TextTestRunner(verbosity=2, stream=output)
    runner.run(suite)
    return output.getvalue()

    
if __name__ == '__main__':
    import draftdatamodel, dbtoolkit, engine
    from filter import *
    db = dbtoolkit.amcatDB(profile=True)
    dm = draftdatamodel.getDatamodel(db)
    e = engine.QueryEngine(dm)

    descriptor = List("test", [dm.article, dm.brand, dm.property, dm.associationcooc], [ValuesFilter(dm.article, 46599856), ValuesFilter(dm.brand, 16545)])

    runTests(e, descriptor)

    
