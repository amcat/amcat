#!/usr/bin/python
###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
Usage: python preprocess.py [-q] ACTION [ANALYSISID] [MAXN/SID] [<ARTICLEIDS/BYTES]

Possible ACTIONs:

stats:  Give statistics about assigned articles
split:  Split the given articles
        Ignores sentences already split
assign: Split the given articles and assign to the given analysis
        Ignores sentences already parsed or assigned.
get:    Get MAXN sentences from the analysis and mark them 'started'
reset:  Set non-complete analyses to not-started
store:  Store BYTES for sentence SID on analysis
save:   Save (maxn) sentences from stored to actual parses tables
        NOTE: SAVE IS NOT THREADSAFE, make sure that 'you' are the only
              process running save at the same time!

if -q is given, only print errors to stderr
"""

import logging; LOG = logging.getLogger(__name__)
import amcatlogging; amcatlogging.setStreamHandler()
import sys, dbtoolkit, analysis, preprocessing, toolkit
try:
    import cPickle as pickle
except:
    import pickle
    
db = dbtoolkit.amcatDB()

def warn(x): print >>sys.stderr, x

def usage(msg=None):
    if msg: warn("%s\n" % msg)
    warn(__doc__)
    warn("\nAvailable analyses:")
    for a in analysis.Analysis.getAll(db):
        if a.id > 0:
            warn(" %i) %s" % (a.id, a.label))
    sys.exit()

def arg(i):
    if len(sys.argv) <= i: usage("The requested action needs at least %i arguments, only %i provided" %
                                 (i, len(sys.argv)-1))
    return sys.argv[i]

verbose = True
if "-q" in sys.argv:
    verbose = False
    del sys.argv[sys.argv.index("-q")]
    amcatlogging.quietModule()
    
def status(s):
    LOG.info(s)

action = arg(1)

if action == "split":
    aids = list(toolkit.intlist())
    status("Splitting %i articles" % len(aids))
    n = preprocessing.splitArticles(db, aids)
    status("%i articles where split, committing" % n)
    db.commit()
    status("Done!")
elif action == "stats":
    t = preprocessing.getStatistics(db)
    import tableoutput
    print tableoutput.table2unicode(t)
elif action in ('assign', 'get', 'reset', 'store', 'save'):
    try:
        analysisid = int(arg(2))
        ana = analysis.Analysis(db, analysisid)
        if ana.id == 0 or (not ana in analysis.Analysis.getAll(db)):
            raise ValueError("Analysis %i does not exist" % analysisid)
    except Exception, e:
        usage(e)
    if action == "assign":
        aids = list(toolkit.intlist())
        status("Assigning %i articles to analysis %s" % (len(aids), ana.idlabel()))
        preprocessing.assignArticles(db, ana, aids)
        db.commit()
        status('Succesfully assigned the articles. Run "preprocess.py stats" to keep track of progress')
    elif action == 'reset':
        status("Resetting 'started' state for non-complete articles in %s" % ana.idlabel())
        preprocessing.reset(db, ana)
        db.commit()
    elif action == 'store':
        sid = int(arg(3))
        results = sys.stdin.read()
        status("Committing %i bytes to sentence %i in %s" % (len(results), sid, ana.idlabel()))
        preprocessing.storeResult(db, ana, sid, results)
        db.commit()
        status("Done")
    elif action == 'get':
        maxn = int(arg(3))
        status("Getting max %i sentences from %s"% (maxn, ana.idlabel()))
        sents = preprocessing.getNonemptySentenceTexts(db, ana, maxn)
        if sents is None:
            status("Queue is empty, printing pickle(None)")
        else:
            status("Printing %i non-empty sentences in pickled list of pairs" % len(sents))
        pickle.dump(sents, sys.stdout, protocol=2)
    elif action == 'save':
        maxn = int(sys.argv[3]) if len(sys.argv) > 3 else None
        status("Saving %s sentences from %s to destination"% (maxn, ana.idlabel()))
        preprocessing.save(db, ana, maxn)
        
else:
    usage("Uknown action: %s" % action)
