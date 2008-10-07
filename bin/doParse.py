#from optparse import OptionParser

#parser.add_option("-p", "--processes", type="int", dest="numprocs", help="Number of processes to start in parallel")
#parser.add_option("-h

import dbtoolkit, sys, toolkit, article, parsetriplestodb, alpino
from toolkit import debug
from threading import Thread, Lock
from Queue import *

toolkit._DEBUG = 2

extrawhere = " and parnr in (1,2)"
extrawhere = ""

# storing the results needs to happen in a separate thread to avoid
# duplicate insertions of the same words resulting in PK violations
class Storer(Thread):
    def __init__(self, q, **kargs):
        Thread.__init__(self, **kargs)
        self.q = q
        self.finish = False
        self.db = dbtoolkit.anokoDB()
        self.c = parsetriplestodb.Converter(self.db)
    def run(self):
        while 1:
            try:
                sid, parse = self.q.get(True, 5)
                debug("[%s] Parse found for sentence %i, adding to db" % (self.getName(), sid))
                try:
                    self.c.convert(sid, parse)
                    self.db.conn.commit()
                except Exception, e:
                    debug("[%s] Exception on adding parse %i to db: %s\n%r" % (self.getName(), sid, e, parse))
            except Empty:
                debug("[%s] No parse found, finish=%s" % (self.getName(), self.finish))
                if self.finish: return
                
                        
    

class Parser(Thread):
    def __init__(self, inputq, outputq, **kargs):
        Thread.__init__(self, **kargs)
        self.inputq = inputq
        self.outputq = outputq
        self.db = dbtoolkit.anokoDB()

    def run(self):
        while 1:
            try:
                aid = self.inputq.get(block=False)
            except Empty:
                debug("[%s] Finished!" % self.getName())
                return
            debug("[%s] Parsing article %i" % (self.getName(), aid))
            parses = parse(aid, self.db)
            if parses:
                debug("[%s] Parsed into %i sentences, placing on output queue" % (self.getName(), len(parses)))
                for sid, prs in parses:
                    self.outputq.put((sid, prs), block=False)
            else: debug("[%s] No parses retrieved? %r" % (self.getName(), parses))
                 
    
def parse(aid, db):
    debug("Parsing article %i" % aid)

    # retrieve sids to parse
    sids = db.doQuery("select sentenceid, sentence from sentences where articleid=%i %s" % (aid, extrawhere))

    if not sids:
        debug("article not in sentences table, performing SBD")
        article.splitArticles([aid], db)
        db.conn.commit()

    sids = db.doQuery("select sentenceid, sentence from sentences where articleid=%i and sentenceid not in (select sentenceid from parses_words) and (len(sentence) > 5) %s" % (aid, extrawhere))

    if not sids:
        debug("SBD failed for article %i, skipping" % aid)
        return

    parses = []

    for sid, sent in sids:
        debug ("Parsing sentence %i:%i (%i words)" % (aid, sid, len(sent.split(" "))))
        if db.doQuery("select * from parses_triples where sentenceid=%i" % sid):
            debug("Sentence already parsed, skipping")
            continue

        err = None
        def errhandler(e): err = e
        try:
            sent = toolkit.stripAccents(sent)
            sent = alpino.tokenize(sent)
            if not " " in sent: continue
            p = alpino.parseTriples(sent, errhandler=errhandler)
            if not p: raise Exception(err)
            parses.append((sid, p))
            debug("Appending sentence to parse")
        except Exception, e:
            debug("Error on parsing sentence, skipping...\n%s" % e)
    
    return parses

inputqueue = Queue()
outputqueue = Queue()

for aid in toolkit.intlist(sys.stdin):
    inputqueue.put(aid)


sys.argv += [9]
NPROC = int(sys.argv[1])
debug("[MAIN] Set up parsing queue with %i items, starting %i worker threads" % (inputqueue.qsize(), NPROC))

threads = set()

for i in range(NPROC):
    w = Parser(inputqueue, outputqueue, name="PT %i" % i)
    w.start()
    threads.add(w)

debug("[MAIN] Set up output thread")
storer = Storer(outputqueue, name="STOR")
storer.start()

debug("[MAIN] Threads started, joining worker threads...")
for thread in threads:
    thread.join()

debug("[MAIN] Worker threads done, closing output thread")
storer.finish = True
storer.join()

debug("[MAIN] Done!")
