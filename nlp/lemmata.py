import toolkit, word, threading, idlabel


class Token(idlabel.Identity):
    def __init__(self, position, word, lemma, poscat, posmajor, posminor):
        self.position = int(position)
        self.word = word
        self.lemma = lemma
        self.poscat = poscat
        self.posmajor = posmajor
        self.posminor = posminor
        self.label = word
    def __repr__(self):
        return "Token(%i, %r, %r, %r, %r, %r)" % (self.position, self.word, self.lemma, self.poscat, self.posmajor, self.posminor)
    def __str__(self):
        return "%s/%s/%s" % (self.word, self.lemma, self.poscat)
    def identity(self):
        return (self.position,  self.word, self.lemma, self.poscat, self.posmajor, self.posminor)



class Lemmata(object):
    def __init__(self, db, analysisid):
        self.db = db
        self.creator = word.WordCreator(db)
        self.analysisid = analysisid
    def addParseWord(self, sid, token):
        wid = self.creator.getWord(token.word, token.lemma, token.poscat)
        posid = self.creator.getPos(token.posmajor, token.posminor, token.poscat)
        self.db.insert("parses_words", dict(analysisid=self.analysisid, sentenceid=sid, wordbegin=token.position, posid=posid, wordid=wid), retrieveIdent=False)

    
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
    #print "Inserting aid %i par %i sent %i text %r" % (art.id, parno, sentno, text)
    return art.db.insert("sentences", dict(articleid=art.id, parnr=parno, sentnr=sentno, sentence=text, encoding=0))

    
