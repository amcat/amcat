#!/usr/bin/python

import sys, dbtoolkit, toolkit
if len(sys.argv) == 1:
    print "Usage: python %s projectid name < articleids" % sys.argv[0]
    print "Or     python %s resultid < articleids" % sys.argv[0]
    sys.exit(1)

db = dbtoolkit.amcatDB()
if len(sys.argv) > 2:
    projectid, name = sys.argv[1:]
    sid = db.insert("storedresults", dict(projectid=projectid, name=name))
    toolkit.warn("Created new storedresult %i"% sid)
else:
    sid = int(sys.argv[1])
toolkit.warn("Adding to storedresult %i"% sid)
for aid in toolkit.intlist():
    db.insert("storedresults_articles", dict(storedresultid=sid, articleid=aid),
              retrieveIdent=False)
db.commit()
