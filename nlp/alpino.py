import toolkit
import lemmata, sentence

ALPINO = "/home/amcat/resources/Alpino"
ALPINO_ANALYSISID = 2

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
          "name" : "M",
          "part" : "R",
          "intensifier" : "B",
          "number" : "Q",
          "reflexive":  'O',
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
        raise Exception("Unknown POS: %r (%s/%s/%s/%s)" % (m2, major, begin, word, pos))
    return lemmata.Token(int(begin), word, lemma, cat, major, minor) 

def line2tokens(line):
    data =line.split("|")
    token1 = data[:7]
    rel = data[7]
    rel = rel.split("/")[-1]
    token2 = data[8:15]
    sid = data[15]
    return data2token(*token1), rel, data2token(*token2), int(sid)

def parseSentenceRaw(sent, errorhook=None):
    if not (sent and sent.strip()): return
    out, err = toolkit.execute(PARSE, sent, listener=errorhook)
    for line in out.split("\n"):
        if not line.strip(): continue
        yield line

def parseSentence(sent, errorhook=None):
    for line in parseSentenceRaw(sent, errorhook):
        t1, rel, t2, sid = line2tokens(line)
        yield t1, rel, t2

def addText(art, text, lem=None):
    sents = tokenizeText(text + " ")
    if lem is None: lem = lemmata.Lemmata(art.db, ALPINO_ANALYSISID)
    sent = None
    for text in sents:
        sent = sent or addSentence(art, lem, text)
    art.db.commit()
    return sent
                                    

def addSentence(art, lem, sent):
    if not (sent and sent.strip()): return
    sid = lemmata.addSentence(art, sent)
    s = sentence.Sentence(art.db, sid)
    parseAndStoreSentence(lem, s)
    return s

def parseAndStoreSentence(lem, sent):
    tokens = {}
    rels = []
    for t1, rel, t2 in parseSentence(sent.text):
        tokens[t1.position] = t1
        tokens[t2.position] = t2
        rels.append((t1.position, t2.position, rel))
    for token in tokens.values():
        lem.addParseWord(sent.id, token)
    duperels = {} # ppos, cpos : rel (to detect dupes)
    for ppos, cpos, rel in rels:
        oldrel = duperels.get((ppos, cpos))
        if oldrel is not None:
            if oldrel == rel: continue
            raise Exception("Cannot store sentence %i: duplicate relation %s->%s (%s <> %s)" % (send.id, ppos, cpos, oldrel, rel))
        duperels[ppos, cpos] = rel
        relid = lem.creator.getRel(rel)
        sent.db.insert("parses_triples", dict(sentenceid=sent.id, parentbegin=ppos, childbegin=cpos, relation=relid, analysisid=ALPINO_ANALYSISID), retrieveIdent=False)

def tokenizeText(text):
    out, err = toolkit.execute(TOKENIZE, text)
    if err:
        raise Exception(err)
    return [x for x in out.split("\n") if x.strip()]

AID = 44569371

    


        
