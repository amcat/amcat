from __future__ import with_statement

import dbtoolkit, article, toolkit, sys, preprocessing
import logging; LOG = logging.getLogger(__name__)
import tadpole
from amcatlogging import logExceptions

ANALYSISID=3

if __name__ == '__main__':
    import amcatlogging; amcatlogging.setStreamHandler()
    db  = dbtoolkit.amcatDB()

    #t = ArticleLemmatiserThread(db, None, None, None)
    #print len(t.getParagraphs(45638337))
    #import sys; sys.exit()
    
    client = tadpole.TadpoleClient(port=9998)
    while True:
        maxn = 1000
        LOG.info("Getting max %i sentences to lemmatise" % maxn)
        sents = list(preprocessing.getSentences(db, ANALYSISID, maxn))
        db.commit()
        if not sents:
            LOG.info("Done!" % len(sents))
            break
        LOG.info("Lemmatising %i sentences" % len(sents))
        for s in sents:
            with logExceptions(LOG):
                text = toolkit.stripAccents(s.text)
                tokens = list(client.process(text))
                #LOG.info("Storing %i tokens for sentence %i" % (len(tokens), s.id))
                result = [("tokens", tokens)]
                preprocessing.storeResult(db, ANALYSISID, s.id, result)
                db.commit()

