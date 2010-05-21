import unittest
import enginebase
import sys
import StringIO
import toolkit

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
        unittest.TestCase.__init__(self)

    def runTest(self):
        debug("Running %s" % (self.shortDescription()))
        t = self.engine.getTable(self.rows, self.columns, self.cellagr, self.filters)
        self.assertTrue(t)
        debug("Got table of size %ix%i" % (len(t.getRows()), len(t.getColumns())))
        self.assertTrue(t.getRows())
        self.assertTrue(t.getColumns())
        
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
        unittest.TestCase.__init__(self)
    def runTest(self):
        debug("Running %s" % (self.shortDescription()))
        q = self.engine.getQuote(self.aid, self.quote)
        self.assertTrue(q)
        print "QUOTE:", q
    def id(self):
        return self.testid
    def shortDescription(self):
        return "Table %s:%s" % (self.testid, self.name)
    
        
    
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
        for engine in engines:
            suite.addTest(descriptor.getTestCase(engine))
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

    
