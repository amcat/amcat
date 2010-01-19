import toolkit, word

class Token(object):
    def __init__(self, position, word, lemma, poscat, posmajor, posminor):
        self.position = int(position)
        self.word = word
        self.lemma = lemma
        self.poscat = poscat
        self.posmajor = posmajor
        self.posminor = posminor
    def __repr__(self):
        return "Token(%i, %r, %r, %r, %r, %r, %r)" % (self.position, self.word, self.lemma, self.morph, self.poscat, self.posmajor, self.posminor)
    def __str__(self):
        return "%s/%s" % (self.lemma, self.poscat)



class Lemmata(object):
    def __init__(self, db):
        self.db = db
        toolkit.ticker.warn("Getting lemmata")
        self.lemmacache = word.LemmaCache(db)
        toolkit.ticker.warn("Getting words")
        self.wordcache = word.WordLemmaCache(db)
        toolkit.ticker.warn("Getting pos")
        self.poscache = word.POSCache(db)
        toolkit.ticker.warn("Getting rels")
        self.relcache = word.RelCache(db)
    def addParseWord(self, sid, token): 
        lid = self.lemmacache.getLemmaID(token.lemma, token.poscat, create=True)
        wid = self.wordcache.getWordID(lid, token.word, create=True)
        posid = self.poscache.getPosID(token.posmajor, token.posminor, token.poscat, create=True)
        self.db.insert("parses_words", dict(sentenceid=sid, wordbegin=token.position, posid=posid, wordid=wid), retrieveIdent=False)

    
def addSentence(art, text, parno=1, sentno=None, retokenize=True):
    #toolkit.ticker.warn("Adding sentence %i:%i" % (parno, sentno))
    if sentno is None:
        maxsent = art.db.getValue("select max(sentnr) from sentences where articleid=%i and parnr=%i" % (art.id, parno))
        sentno = 1 if maxsent is None else maxsent + 1

    if retokenize:
        if type(text) not in (str, unicode):
            text = " ".join(text)
        tokens = text.split(" ")
        text = ""
        for token in tokens:
            if text and token not in (".,)?;:"):
                text += " "
            text += token
    if type(text) == unicode:
        text = text.encode("utf-8")
    print "Inserting aid %i par %i sent %i text %r" % (art.id, parno, sentno, text)
    return art.db.insert("sentences", dict(articleid=art.id, parnr=parno, sentnr=sentno, sentence=text, encoding=0))

    
