import toolkit, time, re


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
    
    

