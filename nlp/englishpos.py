import subprocess, re, toolkit
import preprocesstools
from treebankpos import POS
import parse

LEMMATISER = ['java','-mx500m','-classpath','%(resources)s/jars/stanford-postagger-2010-12-06.jar','edu.stanford.nlp.process.Morphology','STDIN']
TAGGER = ["java","-mx500m","-classpath","%(resources)s/jars/stanford-postagger-2010-12-06.jar","edu.stanford.nlp.tagger.maxent.MaxentTagger","-model","%(resources)s/files/left3words-wsj-0-18.tagger","-textFile","STDIN"]

import logging; log = logging.getLogger(__name__)

def pos2token(position, token):
    word, pos = token.rsplit("/", 1)
    poscat = POS[pos]
    return (position, word, word, poscat, pos,'')

def lemmatise(taglines, resources=None):
    if resources is None: resources = preprocesstools.getResourcesDir()
    lemmacmd = [c % locals() for c in LEMMATISER]
    log.debug("Executing %r" % lemmacmd)
    lemmatiser = subprocess.Popen(lemmacmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    log.debug("Tagger loaded, sending %i sentences" % len(taglines))
    out, err = lemmatiser.communicate("\n".join(taglines))

    if err.strip(): raise Exception("Error on lemmatising %r\n%s" % (taglines, err))
    lemmalines = [l.strip() for l in out.split("\n")]
    if len(lemmalines) <> len(taglines): raise Exception("Lemmata do not mathc words! %r <> %r" % (lemmalines, taglines))
    return lemmalines
    

def postag(input, resources=None):
    if resources is None: resources = preprocesstools.getResourcesDir()
    taggercmd = [c % locals() for c in TAGGER]
    log.debug("Executing %r" % taggercmd)
    tagger = subprocess.Popen(taggercmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    log.debug("Tagger loaded, sending %i bytes" % len(input))
    out, err = tagger.communicate(input)
    if not re.match("Loading default properties from trained tagger.*\\nReading POS tagger model from.*\\nType some text to tag, then EOF.\s*\\n\s+\(For EOF, use Return, Ctrl-D on Unix; Enter, Ctrl-Z, Enter on Windows.\)\s*\nTagged \d+ words at \d+\.\d+ words per second.", err):
        raise Exception("Exception on pos-tagging %r:\n%r" % (input, err))
    return [l for l in out.split("\n") if l.strip()]

def pos2token(position, wordstr, lemmastr):
    try:
        word, pos = wordstr.rsplit("_", 1)
        lemma, pos2 = lemmastr.rsplit(" ", 1)
        if pos <> pos2: raise Exception("POS mismatch %r vs %r" %(wordstr, lemmastr))
        poscat = POS[pos]
        return (position, word, lemma, poscat, pos,'')
    except:
        log.error("Problem with %r / %r" % (wordstr, lemmastr))
        raise

def parseSentences(sentences, resources=None):
    sids, input = preprocesstools.getInputFromSentences(sentences)
    taglines = postag(input, resources)
    lemmalines = lemmatise(taglines, resources)
    for sid, tagline, lemmaline in zip(sids, taglines, lemmalines):
        try:
            tags = tagline.split(" ")
            lemmata = lemmaline.split("   ")
            if len(tags) <> len(lemmata):
                raise Exception("words do not match lemmata tokens: %r vs %r" % (tags, lemmata))
            tokens = [pos2token(p,w,s) for (p, (w, s)) in enumerate(zip(tags, lemmata))]
            yield sid, (('tokens', tokens),)
        except Exception, e:
            log.error("Problem with %s: %r / %r" % (sid, tagline, lemmaline))
            log.error(e)
    
if __name__ == '__main__':
    import amcatlogging; amcatlogging.setup(); amcatlogging.debugModule()
    #print list(parseSentences([(1, "this is crap_this is _        crap 'this'  is \"crapthis\" go \\ so / what?")]))
    
    l = parseSentences([(1, "I've been good!"), (2, "How are you guys?"), (3, ""), (4, "bla\n\nbla")])
    print "\n".join(map(str, l))
