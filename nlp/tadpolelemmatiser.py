import tadpole, word, re, traceback, toolkit, lemmata
import threading, Queue, time

ANALYSISID = 3

class TadpoleLemmatiser(object):
    def __init__(self, articleprovider):
        self.tadpoleclient = tadpole.TadpoleClient(port=9998)
        self.articleprovider = articleprovider
 
    def lemmatiseSentences(self, sentences):
        result = []
        for sid, text in sentences:
            result += self.addSentenceLemmata({'sid':sid}, self.tadpoleclient.process(text))
        return result

    def lemmatise(self, aid):
        result = []
        sentences = self.articleprovider.getSentences(aid)
        if sentences:
            return self.lemmatiseSentences(sentences)
        else:
            return self.lemmatiseText(aid)

    def lemmatiseText(self, aid):
        pars = self.articleprovider.getParagraphs(aid)
        result = []
        for i, par in enumerate(pars):
            if par:
                result += self.addParagraph(aid,i+1,par)
        return result

    def addParagraph(self, aid, parno, text):
        result = []
        tokens = self.tadpoleclient.process(text)
        sentno = 1
        sent = []
        for token in tokens:
            if sent and (token.position <> sent[-1].position+1):
                result += self.addSentence(aid, parno,sentno, sent)
                sent = []
                sentno += 1
            sent.append(token)
        if sent: result += self.addSentence(aid, parno, sentno, sent)
        return result
            
    def addSentence(self, aid, parno, sentno, tokens):
        #toolkit.ticker.warn("Adding sentence %i:%i" % (parno, sentno))
        tokens = list(tokens)
        text = ""
        for tok in tokens:
            tok = tok.word
            if text and tok not in (".,)?;:"):
                text += " "
            text += tok
        text =text.encode("utf-8")
        sent = dict(articleid=aid, parnr=parno, sentnr=sentno, sentence=text, encoding=0)
        #sid = art.db.insert("sentences", dict(articleid=art.id, parnr=parno, sentnr=sentno, sentence=text, encoding=0))
        return self.addSentenceLemmata(sent, tokens)


    def addSentenceLemmata(self, sent, tokens):
        #print "Adding lemmata to sentence %s" % sent
        last = None
        result = []
        for token in tokens:
            if token.position <= last: # prevent mistake in SBD (ie old sentences) from crashing insert
                token.position = last + 1 
            last = token.position
            result.append((sent, token))
        return result

DBLOCK = threading.Lock()
            
class ArticleLemmatiserThread(threading.Thread):
    def __init__(self, db, articleq, resultsq, name):
        threading.Thread.__init__(self, name=name)
        self.db = db 
        self.articleq = articleq
        self.resultsq = resultsq
        self.lemmatiser = TadpoleLemmatiser(self)
            
    def getSentences(self, aid):
        DBLOCK.acquire()
        try:
            a = article.Article(self.db, aid)
            sents = a.sentences
            if sents:
                return [(s.id, toolkit.stripAccents(s.text)) for s in sents]
            else:
                return None
        finally:
            DBLOCK.release()

    def getParagraphs(self, aid):
        DBLOCK.acquire()
        try: 
            result = []
            art = article.Article(self.db, aid)
            result.append(art.headline)
            result.append(art.byline)
            pars = re.split(r"\n\s*\n", self.db.getText(art.id).strip())#.split("\n\n")
            result += [toolkit.stripAccents(re.sub("\s+"," ", par))
                       for par in pars]
            return result
        finally:
            DBLOCK.release()

            
    def run(self):
        while not self.articleq.empty():
            aid = None
            try:
                if self.resultsq.qsize() > 100:
                    time.sleep(1)
                    continue
                aid = self.articleq.get()
                result = self.lemmatiser.lemmatise(aid)
                self.resultsq.put((aid, result))
                #toolkit.ticker.warn("Thread %s, Article %s, #results:%s!" % (threading.currentThread().getName(), aid, result and len(result)))
            except Exception, e:
                toolkit.ticker.warn("Thread %s, Article %s, Exception: %s" % (threading.currentThread().getName(), aid, e))
                traceback.print_exc()

class StorerThread(threading.Thread):
    def __init__(self, db, resultq):
        threading.Thread.__init__(self, name="ST")
        self.db = db
        self.resultq = resultq
        self.canstop = False
        print "Locking"
        DBLOCK.acquire()
        print "Getting lemmata"
        self.creator = word.WordCreator(db)
        print "Releasing"
        DBLOCK.release()
    def run(self):
        while not (self.canstop and self.resultq.empty()):
            try:
                aid, tokens = self.resultq.get(timeout=.2)
                if tokens:
                    tokens = list(tokens)
                    #toolkit.ticker.warn("Thread %s, Article %s, #tokens %s" % (threading.currentThread().getName(),aid, len(tokens)))
                    self.storeTokens(aid, tokens)
                else:
                    pass
                #toolkit.ticker.warn("Thread %s, Got %s" % (threading.currentThread().getName(), tokens))
            except Queue.Empty:
                #toolkit.ticker.warn("Thread %s, No tokens, canstop=%s" % (threading.currentThread().getName(), self.canstop))
                pass

    def storeTokens(self, aid, tokens):
        try:
            # Step 1: lookup all words + pos
            for (sent, token) in tokens:
                #toolkit.ticker.warn("Thread %s, Article %i, Preprocessing token %s" % (threading.currentThread().getName(), aid, token))
                DBLOCK.acquire()
                try:
                    token.wid = self.creator.getWord(token.word, token.lemma, token.poscat)
                    self.db.commit()
                finally:
                    DBLOCK.release()
                    
                DBLOCK.acquire()
                try:
                    token.posid = self.creator.getPos(token.posmajor, token.posminor, token.poscat)
                    self.db.commit()
                finally:
                    DBLOCK.release()
        except Exception, e:
            toolkit.ticker.warn("Thread %s, Article %i, Exception on preprocessing: %s" % (threading.currentThread().getName(), aid, e))
            traceback.print_exc()
            return

        # Step 2: add all tokens in one transaction (so rollback is possible)
        try:
            DBLOCK.acquire()
            for sent, token in tokens:
                #toolkit.ticker.warn("Thread %s, Article %i, Inserting token %s" % (threading.currentThread().getName(), aid, token))
                sid = sent.get("sid")
                if not sid:
                    sid = self.db.insert("sentences", sent)
                    sent["sid"] = sid
                    #toolkit.ticker.warn("Thread %s, Article %i, Created new sentence: %i" % (threading.currentThread().getName(), aid, sid))
                self.db.insert("parses_words", dict(analysisid=ANALYSISID, sentenceid=sid, wordbegin=token.position, posid=token.posid, wordid=token.wid), retrieveIdent=False)
                #toolkit.ticker.warn("Thread %s, Article %i, Inserted token %s" % (threading.currentThread().getName(), aid, token))

            self.db.commit()
        except Exception, e:
            self.db.rollback()
            toolkit.ticker.warn("Thread %s, Article %i, Exception on storing: %s" % (threading.currentThread().getName(), aid, e))
            traceback.print_exc()
        finally:
            DBLOCK.release()

      
def lemmatiseArticles(db, aids, threads=6):
    aidq = Queue.Queue()
    resultq = Queue.Queue()
    for aid in aids:
        aidq.put(aid)
    threads = [ArticleLemmatiserThread(db, aidq, resultq, name="L%i" % i) for i in range(threads)]
    toolkit.ticker.warn("Queue now contains %i articles, %i results" % (aidq.qsize(), resultq.qsize()))
    for t in threads:
        t.start()
    storer = StorerThread(db, resultq)
    storer.start()
    while threads:
        time.sleep(5)
        for t in threads[:]:
            if not t.isAlive():
                toolkit.ticker.warn("Thread died: %s" % t.getName())
                threads.remove(t)
        toolkit.ticker.warn("Queue now contains %i articles, %i results" % (aidq.qsize(), resultq.qsize()))
    toolkit.ticker.warn("Lemmatising done, waiting for storer to exit!")
    storer.canstop = True
    while storer.isAlive():
        time.sleep(1)
        toolkit.ticker.warn("Result Queue now contains %i results" % (resultq.qsize()))
        if resultq.empty():
            toolkit.ticker.warn("Done?")
    toolkit.ticker.warn("Done!")
    
            
if __name__ == '__main__':
    import dbtoolkit, article, toolkit, sys

    BATCH = "(5452,5451,5450,5447,5446,5444,5429,5417,5389,5383,5334,5331,5329,5257,5256,5255,5254)"
    #BATCH = "(5452)"
    BATCH = "(4354,4159,4158)"
    toolkit.ticker.warn("Setting up lemmatiser")
    SQL = """select articleid from articles where batchid in %s and articleid not in 
             (select articleid from sentences s inner join parses_words w on s.sentenceid = w.sentenceid where analysisid=3)
             order by newid()""" % (BATCH)
    db  = dbtoolkit.amcatDB(easysoft=True)
    aids = [aid for (aid,) in db.doQuery(SQL)]
    #aids.remove(44554827)
    #aids = [44554695, 44554696, 44554697, 44554698, 44554699]
    lemmatiseArticles(db, aids)
