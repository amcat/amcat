"""
Start preprocessing on amcat

python dostanford.py ANALYSISID [NPERBATCH]

TODO: create as proper externalscript
"""

from __future__ import with_statement
import re
import toolkit
import dbtoolkit
import amcatlogging
log = amcatlogging.setup()
#amcatlogging.debugModule()
import preprocessing
import sys

def usage():
    print __doc__
    sys.exit()

if len(sys.argv) < 2: usage()
    
analysisid=int(sys.argv[1])

if analysisid == 4: 
    import stanford
    parse = stanford.parseSentences
elif analysisid == 5:
    import englishpos
    parse = englishpos.parseSentences
elif analysisid == 3:
    import dolemmatise
    parse = dolemmatise.parseSentences
else:
    usage()

if len(sys.argv) >= 3:
    maxn = int(sys.argv[2])
else:
    maxn = 100
    
db  = dbtoolkit.amcatDB()

while True:
    log.info("Getting max %i sentences to parse" % maxn)
    sents = list(preprocessing.getSentences(db, analysisid, maxn))
    db.commit()
    if not sents:
        log.info("Done!")
        break
    sents = [(sent.id, sent.text) for sent in sents]
    #log.info("Parsing %i sentences: %r" % (len(sents), sents))
    log.info("Parsing %i sentences: " % (len(sents), ))
    for sid, result in parse(sents):
        log.debug("Storing sentence %i: %r" % (sid, result))
        preprocessing.storeResult(db, analysisid, sid, result)
        log.debug("Committing")            
        db.commit()
        log.debug("Committed")

