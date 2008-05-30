import clemmatizer as lemmatizer
import postag as tagmod
import ctokenizer as tokenizer
import toolkit
_debug = toolkit.Debug("nlptoolkit", 1)

_LEM = None
_TAG = None

def getLemmatizer():
    global _LEM
    if not _LEM:
        _debug(1,"Creating lemmatizer")
        _LEM = lemmatizer.Lemmatizer()
        _debug(2,"Lemmatizer created!")
    return _LEM

def getTagger():
    global _TAG
    if not _TAG:
        _debug(1,"Creating Tagger")
        _TAG = tagmod.Tagger()
        _debug(2,"Tagger created!")
    return _TAG

def TokTagLem(txt):
    _debug(2, "TTL'ing")
    _debug(3, `txt`)
    #print "TTL %r" % txt
    txt = tokenizer.tokenize(txt)
    #print " Tk %r" % txt
    txt = getTagger().tagtext(txt)
    #print " Tg %r" % txt
    txt = getLemmatizer().lemmatizeList(txt)
    #print " TO %r" % txt
    _debug(3, "TTL OK %r" % txt)
    return txt

if __name__ == '__main__':
    import sys
    print TokTagLem(" ".join(sys.argv[1:]))

          
    
        
