import toolkit
import lemmata

ALPINO = "/home/amcat/resources/Alpino"

TOKENIZE = "%s/Tokenization/tok" % ALPINO
PARSE = "ALPINO_HOME=%s %s/bin/Alpino end_hook=dependencies -notk -parse" % (ALPINO, ALPINO)

POSMAP = {"pronoun" : 'O',
          "verb" : 'V',
          "noun" : 'N',
          "preposition" : 'P',
          "determiner" : "D",
          "comparative" : "C",
          "adverb" : "B",
          "adjective" : "A",
          "complementizer" : "C",
          "punct" : ".",
          "conj" : "C",
          "tag" : "?",
          "particle": "R",
          }

def data2token(lemma, word, begin, end, dummypos, dummypos2, pos):
    if "(" in pos:
        major, minor = pos.split("(", 1)
        minor = minor[:-1]
    else:
        major, minor = pos, None
    if "_" in major:
        m2 = major.split("_")[-1]
    else:
        m2 = major
    cat = POSMAP.get(m2)
    if not cat:
        raise Exception("Unknown POS: %r (%s/%s/%s)" % (major, begin, word, pos))
    return lemmata.Token(int(begin), word, lemma, cat, major, minor) 

def line2tokens(line):
    data =line.split("|")
    token1 = data[:7]
    rel = data[7]
    rel = rel.split("/")[-1]
    token2 = data[8:15]
    sid = data[15]
    return data2token(*token1), rel, data2token(*token2), int(sid)

def parseSentence(sent, errorhook=None):
    if not (sent and sent.strip()): return
    out, err = toolkit.execute(PARSE, sent, listener=errorhook)
    for line in out.split("\n"):
        if not line.strip(): continue
        t1, rel, t2, sid = line2tokens(line)
        yield t1, rel, t2

def addText(art, text, lem=None):
    if lem is None: lem = lemmata.Lemmata(art.db)
    sents = tokenizeText(text + " ")
    sid = None
    for sent in sents:
        sid = sid or addSentence(art, lem, sent)
    art.db.commit()
    return sid
                                    

def addSentence(art, lem, sent):
    if not (sent and sent.strip()): return
    sid = lemmata.addSentence(art, sent)
    tokens = {}
    rels = []
    for t1, rel, t2 in parseSentence(sent):
        tokens[t1.position] = t1
        tokens[t2.position] = t2
        rels.append((t1.position, t2.position, rel))
    for token in tokens.values():
        lem.addParseWord(sid, token)
    for ppos, cpos, rel in rels:
        relid = lem.relcache.getRelID(rel)
        art.db.insert("parses_triples", dict(sentenceid=sid, parentbegin=ppos, childbegin=cpos, relation=relid), retrieveIdent=False)
        #print add, t1, rel, t2
    return sid
                                     

def tokenizeText(text):
    out, err = toolkit.execute(TOKENIZE, text)
    if err:
        raise Exception(err)
    return out.split("\n")

AID = 44569371

if __name__ == '__main__':
    import sys, dbtoolkit, article
    if len(sys.argv) <= 1:
        print "Usage: alpino.py [--add] sentence"
        sys.exit()
    add = sys.argv[1] == "--add"
    if add:
        del sys.argv[1]
        db = dbtoolkit.amcatDB(easysoft=True)
        art = article.Article(db, AID)
        lem = lemmata.Lemmata(db)
    sent = " ".join(sys.argv[1:])+" "
    sents = tokenizeText(sent)
    for sent in sents:
        if add:
            addSentence(art, lem, sent)
            db.commit()
        else:
            for t1, rel, t2 in parseSentence(sent):
                print add, t1, rel, t2
        
