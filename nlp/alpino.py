import toolkit
import parse

TOKENIZE = "%s/Alpino/Tokenization/tok" 
PARSE = "ALPINO_HOME=%s/Alpino %s/Alpino/bin/Alpino end_hook=dependencies -notk -parse" 

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
          "conjunct" : 'C',
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
    return (int(begin), word, lemma, cat, major, minor) 

def line2tokens(line):
    data =line.split("|")
    token1 = data[:7]
    rel = data[7]
    rel = rel.split("/")[-1]
    token2 = data[8:15]
    sid = data[15]
    return data2token(*token1), rel, data2token(*token2), int(sid)

class AlpinoParser(parse.Parser):
    analysisid=2
    def __init__(self, errorhook=None):
        self.errorhook = errorhook
        parse.Parser.__init__(self)
    
    def parseSentenceRaw(self, sent):
        resources = parse.getResourcesDir()
        if not (sent and sent.strip()): return
        out, err = toolkit.execute(PARSE % (resources, resources), sent, listener=self.errorhook)
        print "Received\n%s\n---------\n%s" % (out, err)
        for line in out.split("\n"):
            if not line.strip(): continue
            yield line

    def parse(self, sent):
        for line in self.parseSentenceRaw(sent):
            t1, rel, t2, sid = line2tokens(line)
            yield t1, rel, t2

    def tokenizeText(text):
        resources = parse.getResourcesDir()
        out, err = toolkit.execute(TOKENIZE % (resources,), text)
        if err:
            raise Exception(err)
        return [x for x in out.split("\n") if x.strip()]

       
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        toolkit.warn("Usage: alpino.py SENTENCE")
        sys.exit()
    sent = " ".join(sys.argv[1:])
    p = AlpinoParser()
    print "Using %r to parse %r" % (p, sent)
    print "\n".join(map(str, p.parse(sent)))

        
