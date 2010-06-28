from enginebase import QueryEngineBase
import enginebase
import tableserial
import io, socketio
import filter
import datetime
import labelcachefactory
import toolkit

class CachingEngineWrapper(QueryEngineBase):
    def __init__(self, engine, cachedb, caching=True, useengine=True):
        self.engine = engine
        self.nconcepts = max(concept.id for concept in self.engine.model.getConcepts())
        self.cachedb = cachedb
        self.initcache()
        self.caching = caching
        self.useengine = useengine
        self.labelfactory = labelcachefactory.LabelCacheFactory(self.cachedb)
        QueryEngineBase.__init__(self, self.engine.model)
        
    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None, distinct=False):
        result = None
        try:
            result = self.getCachedList(concepts, filters, distinct)
        except Exception, e:
            import traceback
            traceback.print_exc()
        if not result:
            if not self.useengine:
                raise Exception("Result not cached and engine disabled")
            result = self.engine.getList(concepts, filters, distinct=distinct)
            print "got result"
            if self.caching:
                print "caching"
                self.cacheList(result, concepts, filters, distinct)
        enginebase.postprocess(result, sortfields, limit, offset)
        return result 

    def getCachedList(self, concepts, filters, distinct):
        bitmask = self.getBits(concept.id for concept in concepts)
        filtermask = self.getBits(f.concept.id for f in filters)
        SQL = "SELECT id, concepts, filterconcepts, filtervalues FROM listcachetables WHERE (concepts & %s = %s) AND (filterconcepts & %s = filterconcepts)" % (bitmask, bitmask, filtermask)
        if not distinct: SQL += " AND (NOT distnct)"
        print SQL
        for id, cachedconcepts, filterconcepts, filtervalues in self.cachedb.doQuery(SQL):
            print "CHECKING %i" % id
            filterconceptids = [self.engine.model.getConcept(self.nconcepts-1-i) for (i, on) in enumerate(filterconcepts) if on == "1"]
            cachedconceptids = [self.engine.model.getConcept(self.nconcepts-1-i) for (i, on) in enumerate(cachedconcepts) if on == "1"]
            cachefilters = list(deserialiseFilters(filtervalues, filterconceptids))
            tofilter = filterSubsumption(filters, cachefilters)
            if tofilter is None:
                print "Incompatible, skipping"
                continue  # incompatible filters
            if set(f.concept for f in tofilter) - set(cachedconcepts):
                print "Required filter concept not in concepts"
                continue
            return self.getListFromCache(id, concepts, tofilter, distinct)

    def getListFromCache(self, cid, concepts, tofilter, distinct):
        sql = "SELECT %s%s FROM listcachetable_%i" % (distinct and "DISTINCT " or "", ",".join(concept.label for concept in concepts), cid)
        if tofilter:
            sql += " WHERE (%s)" % ") AND (".join(f.getSQL() for f in tofilter)
        
        serialisers = list(tableserial.getColumns(concepts, IDLabelFactory=self.labelfactory))
        data = []
        print sql
        for row in self.cachedb.doQuery(sql):
            data.append([s.deserialiseSQL(val) for (s, val) in zip(serialisers, row)])
        return enginebase.ConceptTable(concepts, data)
            
    
    def getQuote(self, article, words):
        words = " ".join(toolkit.getQuoteWords(words))
        try:
            q = self.getCachedQuote(article, words)
            if q:
                toolkit.warn("Retrieved quote from cache")
            else:
                toolkit.warn("Querying underlying engine for quote")
                q = self.engine.getQuote(article, [words])
                self.cacheQuote(article, words, q)
            return q
        except:
            return self.engine.getQuote(article, [words])        
                                                      
    
    def initcache(self):
        if not self.cachedb.hasTable("listcachetables"):
            print "Creating cache tables"
            for cmd in CACHE_INIT_SQL:
                self.cachedb.doQuery(cmd % self.__dict__)
            self.cachedb.commit()

    def getBits(self, conceptids, returnStr=False): 
        conceptids = set(conceptids)
        if returnStr:
            return "".join(("1" if (self.nconcepts-1-id) in conceptids else "0") for id in range(self.nconcepts))
        bitmask = sum(2**cid for cid in conceptids)
        return "%i::bit(%i)" % (bitmask, self.nconcepts)
            
    def cacheList(self, table, concepts, filters, distinct):
        bitmask = self.getBits((concept.id for concept in concepts), returnStr=True)
        filtermask = self.getBits((f.concept.id for f in filters), returnStr=True)
        filtervalues = serialiseFilters(filters)
        cid = self.cachedb.insert("listcachetables", dict(concepts=bitmask, filterconcepts=filtermask,
                                                          filtervalues = filtervalues, distnct=distinct))

        #cid = self.cachedb.getValue("select currval('listcachetables_id_seq')")
        serialisers = list(tableserial.getColumns(concepts))
        tablename = "listcachetable_%i" % cid
        columns = getColumnNames(concepts)
        createsql = "CREATE TABLE %s (\n%s)" % (tablename, ",\n".join(
                "%s %s" % (c, s.getSQLType()) for (c,s) in zip(columns, serialisers)))
        self.cachedb.doQuery(createsql)
        self.cachedb.insertmany(tablename, columns, ([s.serialiseSQL(v) for (s,v) in zip(serialisers, row)] for row in table))
        self.cachedb.commit()

def getColumnNames(concepts):
    result = []
    for concept in concepts:
        l = concept.label
        if l in result:
            for i in xrange(100):
                l2 = "%s_%i" % ( l, i)
                if l2 not in result: break
            l = l2
        result.append(l)
    toolkit.warn("getColumnNames(%s)->%s" % (concepts, result))
    return result
        
FILTERTYPE_VALUES, FILTERTYPE_INTERVAL = 1,2
# Filter serialisation protocol
# filters in ascending order of conceptid
# for each filter:
#   integer filtertype: 1 = values, 2 = interval, 3+ reserved
#   if valuefilter:
#      integer nvalues
#      tableserial.serialise each value
#   if intervalfilter:
#      tableserial.serialise from
#      tableserial.serialise to
        
def serialiseFilters(filters):
    bytes = io.BytesIO()
    w = socketio.AmcatSocket(bytes)
    for f in sorted(filters, key=lambda f : f.concept.id):
        ser = tableserial.getColumn(f.concept)
        if type(f) == filter.ValuesFilter:
            w.sendunsigned(FILTERTYPE_VALUES)
            w.sendunsigned(len(f.values))
            for val in f.values:
                ser.serialiseValue(val, w)
        else:
            w.sendunsigned(FILTERTYPE_INTERVAL)
            for val in f.fromValue, f.toValue:
                ser.serialiseValue(val, w)
    w.flush()
    return buffer(bytes.getvalue())

def deserialiseFilters(bytes, concepts):
    bytes = io.BytesIO(str(bytes))
    w = socketio.AmcatSocket(bytes)
    
    for concept in sorted(concepts, key=lambda c : c.id):
        ser = tableserial.getColumn(concept)
        ftype = w.readunsigned()
        if ftype == FILTERTYPE_VALUES:
            n = w.readunsigned()
            values = [ser.deserialiseValue(w) for i in range(n)]
            yield filter.ValuesFilter(concept, *values)
        else:
            fromval = ser.deserialiseValue(w)
            toval = ser.deserialiseValue(w)
            yield filter.IntervalFilter(concept, fromval, toval)

def filterSubsumption(filters, cachefilters):
    filters = dict((f.concept.id, f) for f in filters)
    for cf in cachefilters:
        f = filters[cf.concept.id]
        ser = tableserial.getColumn(f.concept)
        if type(f) <> type(cf):
            print "Incompatible filters: %s / %s" % (f, cf)
            return None
        if type(f) == filter.ValuesFilter:
            fvals, cfvals  = set(map(ser.serialiseSQL, f.values)), set(map(ser.serialiseSQL,cf.values))
            if fvals == cfvals:
                del filters[cf.concept.id] # identical
            if fvals - cfvals:
                print "Not all filter values included in cache filter %s - %s != {}" % (fvals, cfvals)
                return None
        else:
            ff, ft, cff, cft = map(ser.serialiseSQL, [f.fromValue, f.toValue, cf.fromValue, cf.toValue])
            if ff==cff and ft == cft:
                del filters[cf.concept.id] # identical
            else:
                print ff, cff, ft, cft
                if ff != cff and ff < cff: return None
                if ft != cft and ft > cft: return None
    return filters.values()
        
CACHE_INIT_SQL = [
    """create table listcachetables (
       id serial primary key,
       concepts bit(%(nconcepts)i),
       filterconcepts bit(%(nconcepts)i),
       filtervalues bytea,
       distnct boolean)""",
    """create table quotecache (
       aid integer,
       words varchar(4000),
       quote varchar(4000),
       primary key (aid, words))"""
    ]

if __name__ == '__main__':
    import amcatmetadatasource, engine, dbtoolkit, psycopg2, filter, config, tableoutput

    # filter serialise test
    # date = amcatmetadatasource.getDataModel(None).date
    # f = filter.IntervalFilter(date, datetime.date(2010,4,1))
    # print f
    # bytes = serialiseFilters([f])
    # print `str(bytes)`
    # f2 = list(deserialiseFilters(bytes, [date]))
    # print f2
    # import sys; sys.exit(1)
    
    
    db = dbtoolkit.amcatDB()
    e = engine.QueryEngine(amcatmetadatasource.getDataModel(db), db)
    cnf = config.Configuration(driver=psycopg2, username="proxy", password='bakkiePleuah', database="proxy", host="localhost", keywordargs=True)
    cdb = dbtoolkit.amcatDB(cnf)
    w = CachingEngineWrapper(e, cdb, caching=True)
    
    l = w.getList([w.model.article, w.model.headline, w.model.date, w.model.source, w.model.storedresult], [filter.ValuesFilter(w.model.storedresult, 765), filter.ValuesFilter(w.model.source, 5)], limit=10)
    print tableoutput.table2unicode(l)
    

