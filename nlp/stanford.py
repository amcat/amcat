import subprocess, re, toolkit
from treebankpos import POS
import preprocesstools

import logging; log = logging.getLogger(__name__)

CMD = ['java','-cp','%(resources)s/jars/stanford-parser-2008-10-30.jar','-mx600m','edu.stanford.nlp.parser.lexparser.LexicalizedParser','-sentences','-retainTMPSubcategories','-outputFormat','wordsAndTags,typedDependencies','-outputFormatOptions','stem,basicDependencies','%(resources)s/files/englishPCFG.ser.gz','-']

def interpreterr(err):
    for line in err.split("\n"):
        m = re.match(r"Parsing \[sent. (\d+) len. \d+\]: \[(.*)\]", line.strip())
        if m:
            i, sent = m.groups()
            yield int(i)-1, sent.split(", ") # to get 0-based offset

def interpretout(out):
    # output of correctly parsed sentences is of form
    # tokens / empty / triple / ... / triple / empty
    # output of error is of form
    # Sentence skipped: / SENTENCE_SKIPPED (no empty line)
    lines = out.split("\n")
    i = -1 # start with index -1 + 1 = 0
    def expect(s):
        line = lines.pop(0)
        if line.strip() <> s: raise Exception("Expected %r, got %r" % (s, line))
    while lines:
        tokens = lines.pop(0)
        if not tokens: continue # skip leading empty lines
        i += 1
        if tokens.startswith("Sentence skipped:"):
            expect("SENTENCE_SKIPPED_OR_UNPARSABLE")
            log.warn("Sentence #%i was skipped or unparsable" % i)
            log.debug("Lines now %r" % lines)
            continue
        tokens = tokens.split(" ")

        log.debug("Read tokens %r, reading triples..." % tokens)
        log.debug("Lines now %r" % lines)
        
        triples = []
        expect("")
        while True:
            triple = lines.pop(0)
            log.debug("Read triple %r..." % triple)
            log.debug("Lines now %r" % lines)
            if not triple: break
            m = re.match(r"([\w&]+)\(.+-(\d+), .+-(\d+)\)", triple)
            if not m: raise Exception("Cannot interpret triple %s" % triple)
            rel, p1, p2 = m.groups()
            triple = (int(p1)-1, rel, int(p2)-1)
            triples.append(triple)
        log.debug("Done! i=%i, tokens=%s, triples=%s" % (i, tokens, triples))
        yield i, tokens, triples

def pos2token(position, w, s):
    lemma, pos = s.rsplit("/", 1)
    poscat = POS[pos]
    return (position, w, lemma, poscat, pos,'')


def parseSentences(sentences, resources=None):
    if resources is None: resources = preprocesstools.getResourcesDir()
    cmd = [c % locals() for c in CMD]
    log.debug(cmd)
    
    parser = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    sids, text = preprocesstools.getInputFromSentences(sentences)
    log.debug("Sending %s" % (text,))
    out, err = parser.communicate(text)
    if "*******" in err:
        log.warn(err) # *** indicates error
    else:
        log.debug(err)

    wordtokendict = dict(interpreterr(err))

    for (i, lemmatokens, triples) in interpretout(out):
        sid, sent = sentences[i]
        wordtokens = wordtokendict[i]
        if len(wordtokens) != len(lemmatokens):
            log.warn("Words %s do not match lemmata %s, skipping!" % (wordtokens, lemmatokens))
            continue
        tokens = [pos2token(p,w,s) for (p, (w, s)) in enumerate(zip(wordtokens, lemmatokens))]
        log.debug("Sentence %i, Tokens: %r, Triples: %r" % (sid, tokens, triples))
        yield sid, (('tokens', tokens), ('triples', triples))


#import amcatlogging; amcatlogging.debugModule()
        
if __name__ == '__main__':
    import amcatlogging; amcatlogging.setup()
    #amcatlogging.debugModule()
    import sys
    if len(sys.argv) < 2:
        toolkit.warn("Usage: stanford.py SENTENCE")
        sys.exit()
    sent = " ".join(sys.argv[1:])
    l = parseSentences([(1, sent), (99, ""), (300, "another sentnece")])
    #l = parseSentences([(1, sent), (99, "this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long this is another sentence that is very long "), (3000, "this one is ok")])
    print "\n".join(map(str, l))
        


    

        
    
