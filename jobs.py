#! /usr/bin/python

import dbtoolkit, random, toolkit, re, math


def updateSetCoder(jobid, setnr, coder):
    pass



def addJob(coders, name="-", ids=[], setsize=None, artschema=3, arrowschema=1, params=None, 
                batchid=None, inetversion=None, priority=0, db=None, projectid=None, overlap=None):

    if not db:
        db = dbtoolkit.anokoDB()
    if batchid:
        ids = [x[0] for x in db.doQuery("select articleid from articles where batchid=%i" % batchid)]
        if not ids:
            toolkit.warn("Batch %i is empty or does not exist" % batchid)
            return
        if name == "-":
            name = db.doQuery("select name from batches where batchid=%i" % batchid)[0][0]
    if not ids:
        raise Exception('No article ids defined')
    if not coders:
        raise Exception('Missing coders')
            
    random.shuffle(ids)
    if overlap:
        if overlap.endswith('%'):
            overlap = int(math.ceil( float(re.sub('[^0-9]', '', overlap)) / 100.0 * len(ids) ))
        elif overlap.isdigit():
            overlap = int(overlap)
        if type(overlap) == int:
            overlapIds = ids[0:overlap]
            ids = ids[overlap:]
        else:
            raise Exception('Invalid overlap specified')
    else:
        overlapIds = []
        
        
    if not setsize:
        setsize = int(math.ceil(len(ids) / float(len(coders))))
    if len(ids) / setsize > 250:
        raise Exception('This job would use too many sets. Please decrease the job size or increase the set size')

    toolkit.warn("Creating job %s with %i articles to coders %s%s" %
                 (name, len(ids), coders, setsize and "in sets of %i" % setsize or ""))


    toolkit.warn("Creating codingjob.. ", newline=False)
    vals = {'name': name, 'unitschemaid' : arrowschema, 'articleschemaid' : artschema, 'projectid':projectid}
    if params: vals['params'] = params
    if inetversion: vals['inetversion'] = inetversion
    if priority: vals['priority'] = priority
    jobid = db.insert("codingjobs", vals)
    toolkit.warn(jobid)

    curcoder = 0
    numberOfSets = max( int(math.ceil(len(ids) / float(setsize))), len(coders) )
    ntot = len(ids) + len(overlapIds)
    for setnr in range(1, numberOfSets + 1):
        toolkit.warn("Creating codingset %i for user %i.. " % (setnr, coders[curcoder]), newline = False)
        db.insert('codingjobs_sets', {'codingjobid':jobid, 'setnr' : setnr, 'coder_userid' : coders[curcoder]},
                        retrieveIdent = False)
        curcoder += 1
        if curcoder >= len(coders): curcoder = 0
        for overlapId in overlapIds:
            db.insert('codingjobs_articles', {'codingjobid' : jobid, 'setnr' : setnr, 'articleid' : overlapId}, 
                retrieveIdent = False)
        for aid in ids[0:setsize]:
            db.insert('codingjobs_articles', {'codingjobid' : jobid, 'setnr' : setnr, 'articleid' : aid}, 
                retrieveIdent = False)
        ids = ids[setsize:]
    if len(ids) > 0:
        raise Exception('Still ids available. Please report this error. %s %s %s %s' % (len(ids), len(overlapIds), numberOfSets, len(coders)))
    
    
    db.conn.commit()
    
    return (numberOfSets, ntot, jobid)

    