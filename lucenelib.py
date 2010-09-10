import toolkit, time, re
from cachable import Cachable

classpath = '/home/amcat/resources/jars/lucene-core-2.3.2.jar:/home/amcat/resources/jars/msbase.jar:/home/amcat/resources/jars/mssqlserver.jar:/home/amcat/resources/jars/msutil.jar:/home/amcat/libjava:/home/amcat/resources/jars/lucene-highlighter-2.3.2.jar:/home/amcat/resources/jars/jutf7-0.9.0.jar'

def addToIndex(directory, aids):
    cmd = 'java -classpath %s AnokoIndexer "%s" append' % (classpath, directory)
    
    inputText = '\n'.join(map(str, aids))
    outputMessage, errorMessage = toolkit.execute(cmd, input=inputText)
    return outputMessage, errorMessage


def search(indexLocation, queryList, startNum=0, endNum=-1, startDate=None, endDate=None, 
                useParagraphs=False, mediumids=[], db=None):
    classp = classpath
    cmd = """java -classpath %(classp)s \
    -Xmx500M \
    AnokoSearch2 "%(indexLocation)s" - csv \
                %(startNum)s %(endNum)s""" % locals()
    if startDate and endDate and endDate < startDate:
        raise Exception('Invalid date selection. End date is before begin date')
    if startDate:
        cmd += ' %s' % startDate
        if not endDate:
            cmd += ' 21000101'
    if endDate:
        if not startDate:
            cmd += ' 19000101'
        cmd += ' %s' % endDate
    if mediumids:
        if not (startDate or endDate):
            cmd += ' 19000101 21000101'
        cmd += ' %s' % ':'.join(map(str, mediumids))

    print "@@@@@@@@@@@@",startDate, endDate, cmd
    
    if type(queryList) == str:
        raise Exception('invalid query type, should be iterable')
    inputText = '\n'
    for i, (identifier, keyword) in enumerate(queryList):
        inputText += '%s\t%s\n' % (i, keyword)
    inputText = inputText.encode('utf-8')
        
    startTime = time.time()

    out, errorMsg = toolkit.execute(cmd, input=inputText)
    
    endTime = time.time()
    totalTime = endTime - startTime

    if errorMsg.find('Exception') > -1:
        errorMsg = re.sub('org.apache.lucene.queryParser.', '', errorMsg) # make the error message more user readable
        errorMsg = re.sub('<EOF>', '<End of Line>', errorMsg) # make the error message more user readable
        raise Exception(errorMsg)
        
    if not out:
        return None, totalTime, 0
    aidsDict = toolkit.DefaultDict(dict)
    totalHits = None

    for line in out.split('\n'):
        
        if not line.strip(): continue
        if line.startswith('ndocs:'):
            totalHits = line.split(':')[1]
            continue
        split = line.split('\t')
        identifier = queryList[int(split[0])][0]
        aid = int(split[1])
        date = split[3]
        mediumid = int(split[4])
        hits = int(split[5])
        date = '%s-%s-%s' % (date[0:4], date[4:6], date[6:8])
        
        if useParagraphs:
            paragraph = int(split[2])
            key = (aid, paragraph)
        else:
            key = aid
            if key in aidsDict[identifier]:
                aidsDict[identifier][key]['hits'] += hits
                continue
        artDict = {'date':date, 'hits':hits, 'mediumid':mediumid, 'id':aid}
        #artDict['article'] = article.Article(db, aid, None, mediumid, toolkit.readDate(date), None, None, None)
        aidsDict[identifier][key] = artDict
    if not totalHits:
        totalHits = len(out.split('\n')) - 1
    #addToCache(cacheKey, aidsDict, totalHits)
    return aidsDict, totalTime, totalHits
    
    
def wf(index, operation, aids = None):
    input = aids and "\n".join(str(a) for a in aids)
    cmd = 'java WordFrequency "%s" %s' % (index, operation)
    o, e = toolkit.execute(cmd)
    if e and e.strip(): raise Exception("Error on executing: %s\n%s"% (cmd, e))
    for line in o.split("\n"):
        if not line.strip(): continue
        data = list(line.split("\t"))
        for i in range(len(data)):
            try:
                if not data[i]: data[i] = None
                data[i] = int(data[i])
            except:
                pass # hey, at least I tried!
        yield data


class Index(Cachable):
    __table__ = 'indices'
    __idcolumn__ = 'indexid'
    def __init__(self, db, id, location = None):
        Cachable.__init__(self, db, id)
        self.addDBProperty("location", "directory")
        if location:
            self.cacheValues(location = location)

    def count(self, objects, *args, **kargs):
        objects = clean(objects)
        query = objects.items()
        aidsDict, totalTime, totalHits = search(self.location, query, *args, **kargs)
        for oid, hits in aidsDict.iteritems():
            #o = os[oid]
            for a, info in hits.iteritems():
                if self.db is not None:
                    try:
                        a = self.db.article(a)
                    except Exception, e:
                        toolkit.warn(e)
                        continue
                hits = info['hits']
                yield (oid, a, hits)

    def articlewordfreqs(self, aids=None, thres=None):
        for a, obj, hits in wf(self.location, "COUNT", aids):
            if self.db is not None:
                a = self.db.article(a)
            if hits < thres: continue
            yield a, obj, hits
                
    def wordfreqs(self, aids=None, thres=None, sort=False, ns=False):
        operation = "COUNTALLNS" if ns else "COUNTALL"
        counts = wf(self.location, operation, aids)
        if sort:
            counts = list(counts)
            counts.sort(key = lambda x:x[-1], reverse=True)
        for f in counts:
            if f[-1] < thres: continue
            yield f[0], f[-1] 

    def n(self):
        out = dict(wf(self.location, "INFO"))
        return out["#Documents"], out["#Terms"]

def clean(query):
    if type(query) == dict:
        result = {}
        for k, v in query.iteritems():
            result[k] = clean(v)
        return result
    else:
        if type(query) == str:
            try:
                query = query.decode('utf-8')
            except:
                query = query.decode('latin-1')
        query = toolkit.stripAccents(query)
        query = re.sub("\s+"," ", query)
        query = query.strip()
        return query
        

    
def testQueries(queries, index=None):
    if index is None: index = Index(None, None, location="/home/amcat/indices/testindex")
    toolkit.ticker.warn("Starting test", estimate=len(queries))
    errors = []
    for q in queries.values():
        toolkit.ticker.tick()
        try:
            list(index.count({1:q}))
        except Exception, e:
            errors.append((q, e))
    if errors:
        raise Exception("Errors in queries:\n%s" % "\n".join("[%s] %s" % x for x in errors))
        
if __name__ == '__main__':
    import dbtoolkit
    i = Index(dbtoolkit.amcatDB(), 435)
    for wf in i.wordfreqs(thres=5, sort=True):
        print wf

