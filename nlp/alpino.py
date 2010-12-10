import  re, toolkit
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
          'adv' : 'B',
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
          "cat" : "Q",
          "n" : "Q",
          "reflexive":  'O',
          "conjunct" : 'C',
          "pp" : 'P',
          'anders' : '?',
          'etc' : '?',
          'enumeration': '?',
          'np': 'N',
          'p': 'P',
          'quant': 'Q',
          'sg' : '?',
          'zo' : '?',
          'max' : '?',
          'mogelijk' : '?',
          'sbar' : '?',
          '--' : '?',
                    }

class AlpinoParser(parse.Parser):
    def __init__(self, resources):
        self.resources = resources
        parse.Parser.__init__(self)

def tokenize(sentences):
    resources = parse.getResourcesDir()
    cmd = TOKENIZE % resources
    if sentences[-1] != "\n": sentences += "\n"
    return toolkit.execute(cmd, sentences, outonly=True)

def clean(sent):
    return toolkit.clean(sent, level=1, keeptabs=False)

def parseRaw(input):
    resources = parse.getResourcesDir()
    cmd = PARSE % (resources, resources)
    out, err = toolkit.execute(cmd, input)
    return out

def splitRawParse(rawparse):
    curid = None
    cur = []
    for line in rawparse.split("\n"):
        if "|" not in line: continue
        sid = int(line.split("|")[-1])
        if sid != curid:
            if cur:
                yield curid, cur
            curid = sid
            cur = []
        cur.append(line)
    if cur:
        yield curid, cur


        
def interpret(parse):
    words, triples = {}, []
    lines = map(line2tokens, parse)
    for parent, rel, child in lines:
        for node in parent, child:
            words[node[0]] = node
        triples.append((parent[0], rel, child[0]))
    words = sorted(words.values())
    print words, triples
    return words, triples
        
def parseSentences(sentences):
    input = "\n".join("%i|%s" % (sid, clean(sent)) for (sid, sent) in sentences)
    input = tokenize(input)
    rawparse = parseRaw(input)
    for sid, parse in splitRawParse(rawparse):
        words, triples = interpret(parse)
        yield sid, (('tokens', words), ('tiples', triples))

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
    return data2token(*token1), rel, data2token(*token2)

        
if __name__ == '__main__':
    #zin  ="dit, waarde heer, is 'een' zin"
    input = [(123, "hij 'koopt' bloemen"), (456,"dat is, mooi")]
    #p = BaseAlpinoParser()
    #print p.parse(1234, zin)
    #p.stop()
    import amcatlogging; log = amcatlogging.setup()
    log.info("Parsing %r" % input)
    for sid, info in  parseSentences(input):
        print sid
        print "\n".join(map(str, info))
