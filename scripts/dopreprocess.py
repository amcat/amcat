"""
Start preprocessing on amcat

python dostanford.py ANALYSISID [NPERBATCH]

TODO: create as proper externalscript
"""

import re
from amcat.tools import toolkit
from amcat.db import dbtoolkit
from amcat.tools.logging import amcatlogging
log = amcatlogging.setup()
amcatlogging.debugModule()
from amcat.nlp import preprocessing
import sys

def usage():
    print __doc__
    sys.exit()

if len(sys.argv) < 2: usage()
    
analysisid=int(sys.argv[1])

if analysisid == 2:
    from amcat.nlp import alpino
    parse = alpino.parseSentences
elif analysisid == 4: 
    from amcat.nlp import stanford
    parse = stanford.parseSentences
elif analysisid == 5:
    from amcat.nlp import englishpos
    parse = englishpos.parseSentences
elif analysisid == 3:
    from amcat.nlp import dolemmatise
    parse = dolemmatise.parseSentences
else:
    print "Unknown analysis: %s" % analysisid
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
    sents = [(sent.id, sent.sentence) for sent in sents]
    #log.info("Parsing %i sentences: %r" % (len(sents), sents))
    log.info("Parsing %i sentences: " % (len(sents), ))
    for sid, result in parse(sents):
        log.debug("Storing sentence %i: %r" % (sid, result))
        preprocessing.storeResult(db, analysisid, sid, result)
        log.debug("Committing")            
        db.commit()
        log.debug("Committed")

