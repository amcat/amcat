import toolkit, pickle, re, lemmatizer

_DICTFILE = '/home/anoko/resources/files/deelwwdict.pickled'

def readFromCD(cdfile):
    result = {}
    ticker = toolkit.Ticker(10000)
    toolkit.debug("Reading lemmadict...")
    lem = lemmatizer.Lemmatizer(["-l","-p","-g"])
    toolkit.debug("Reading CELEX CD file...")
    for line in cdfile.readlines():
        ticker.tick()
        m = re.search(r'\d+\\(\w+)\\(\d+)\\.*?\(\((\w+)\)\[P\],\((\w+)\)\[(.)\]\)\[V\]\\', line)
        if not m: continue
        wrd, freq, prep, c2, c2type = m.groups()
        
        #if c2type == 'V':
        #    c2l = lem.lemmatize('%s/V' % c2)
        #else:
        c2l = wrd[len(prep):]
        if c2l[-2] == c2l[1]: c2l = c2l[:-1]
            
        if prep not in result: result[prep] = {}
        if line[:3]=='930':
            print prep, c2l, wrd, int(freq)
        result[prep][c2l] = wrd, int(freq)
        
    return result
    
def readDict(dictfile):
    toolkit.debug('Reading dictionary from file "%s"' % dictfile)
    return pickle.load(open(dictfile))

def writeDict(dict, dictfile):
    toolkit.debug('Writing dictionary (%s entries) to file "%s"' % (len(dict), dictfile))
    pickle.dump(dict, open(dictfile, 'w'))

    
       
class deelww:
    def __init__(self, dictfile=_DICTFILE, cdfile=None):
        if cdfile:
            self.dict = readFromCD(cdfile)
            if dictfile:
                writeDict(self.dict, dictfile)
        elif dictfile:
            self.dict = readDict(dictfile)
        else:
            raise Exception("No dictionary file or cdfile given! Need input!")

    def query(self, prep, verbs=None, returnOriginalVerb=0):
        if verbs==None: return self.dict.get(prep, {})
        hf = 0; cand = None;
        
        for l, (vb, f) in self.query(prep).items():
            
            if l in verbs and f > hf:
                hf = f
                if returnOriginalVerb:
                    cand = (vb, l)
                else:
                    cand = vb
                
        return cand
        
    
if __name__ == '__main__':
    import sys
    toolkit._DEBUG=1
    if sys.argv[1] == '--create-dict': deelww(_DICTFILE, sys.stdin)
    else:
        print deelww(_DICTFILE).query(sys.argv[1], sys.argv[2:])
