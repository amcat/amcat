class Lemmatizer(object):

    def __init__(self, db):
        self.poslemma, self.wordlemma = {}, {}
        self.db = db
        self.cache()

    def cache(self):
        SQL = """select word, pos, l.lemmaid, freq from words_words w inner join words_lemmata l on w.lemmaid = l.lemmaid"""
        wfreqs = {}
        for w, p, l, f in self.db.doQuery(SQL):
            w = w.lower()
            self.poslemma[w,p] = getLemma(self.db, l)
            if f > wfreqs.get(w, -1):
                self.wordlemma[w] = getLemma(self.db,l)
                wfreqs[w] = f
        SQL = """select lemma, pos, lemmaid from words_lemmata"""
        for l,p,lid in self.db.doQuery(SQL):
            l = l.lower()
            if (l,p) not in self.poslemma: self.poslemma[l,p] = getLemma(self.db,lid)
            if l not in self.wordlemma: self.wordlemma[l] = getLemma(self.db, lid)
            

    def getLemma(self, word, pos=None, lenient=True):
        word = word.lower()
        if (word, pos) in self.poslemma: return self.poslemma[word, pos]
        if (lenient or not pos) and word in self.wordlemma: return self.wordlemma[word]
        return None

    def addLemma(self, lemma, pos ,word):
        word = word.lower()
        lemma = lemma.lower()
        lemmaid = self.db.insert("words_lemmata", {"lemma":lemma, "pos":pos})
        #print "Created lemma %i: %s/%s/%s" % (lemmaid, word, pos, lemma)
        l = getLemma(self.db, lemmaid)
        if word:
            self.db.insert("words_words", {"lemmaid": lemmaid, "word" : word})
            if word not in self.wordlemma: self.wordlemma[word] = l
            self.poslemma[word, pos] = l
        if lemma not in self.wordlemma: self.wordlemma[lemma] = l
        if (lemma, pos) not in self.poslemma: self.poslemma[lemma, pos] = l
        return l


lemmacache = {}
def getLemma(db, id):
    global lemmacache
    if id not in lemmacache:
        lemmacache[id] = Lemma(id,db)
    return lemmacache[id]
    

class Lemma(object):
    def __init__(self,lemmaid, db=None):
        self.db = db
        self.lemmaid = lemmaid
        self._lemma, self._pos = None, None

    def getLemma(self):
        if not self._lemma: self.getLP()
        return self._lemma
    def getPos(self):
        if not self._pos: self.getLP()
        return self._pos

    def getLP(self):
        self._lemma, self._pos = self.db.doQuery("select lemma, pos from words_lemmata where lemmaid=%i" % self.lemmaid)[0]

    def __str__(self):
        if self._lemma: return "|%s/%s|" % (self._lemma, self._pos)
        return "Lemma(%i)" % self.lemmaid

if __name__ == '__main__':
    import sys,dbtoolkit
    l = Lemmatizer(dbtoolkit.anokoDB())
    lem = l.getLemma(*sys.argv[1:])
    if lem:
        print lem.getLemma(), lem.getPos()
    
