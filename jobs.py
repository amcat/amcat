#! /usr/bin/python

import dbtoolkit, random, toolkit


def updateSetCoder(jobid, setnr, coder):
    pass



def addJob(coders, name="-", ids=[], setsize=None, artschema=3, arrowschema=1, params=None, 
                batchid=None, inetversion=None, priority=0, db=None, projectid=None):

    if not db:
        db = dbtoolkit.anokoDB()
    if batchid:
        ids = [x[0] for x in db.doQuery("select articleid from articles where batchid=%i" % batchid)]
        if not ids: toolkit.warn("Batch %i is empty or does not exist" % batchid)
        if name == "-":
            name = db.doQuery("select name from batches where batchid=%i" % batchid)[0][0]

    random.shuffle(ids)

    if len(coders)>1 and not setsize:
        setsize = len(ids) / len(coders) + 1

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
    setnr = 0


    ntot = 0
    ncur = 0
    for id in ids:
        if not setnr or setsize and ncur >= setsize:
            if ncur: toolkit.warn("%i articles" % ncur)
            setnr += 1
            toolkit.warn("Creating codingset %i for user %i.. " % (setnr, coders[curcoder]), newline = False)
            db.insert('codingjobs_sets', {'codingjobid':jobid, 'setnr' : setnr, 'coder_userid' : coders[curcoder]}, retrieveIdent = False)
            curcoder += 1
            if curcoder >= len(coders): curcoder = 0
            ncur = 0
        db.insert('codingjobs_articles', {'codingjobid' : jobid, 'setnr' : setnr, 'articleid' : id}, retrieveIdent = False)
        ncur += 1
        ntot += 1
    if ncur: toolkit.warn("%i articles" % ncur)
    
    db.conn.commit()
    
    
    return (setnr, ntot, jobid)

    