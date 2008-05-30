import dbtoolkit, re, toolkit,sys, article
from toolkit import writeDate, log2
ticker = toolkit.Ticker(1000)

def LWt_linear(f): return f
def LWt_logarithmic(f): return toolkit.log2(1.0 + f)
class GWt_trivial:
    def __getitem__(dummy1, dummy2): return 1
def GWt_fromdict(d, wordlist):
    return [d[word] for word in wordlist]

def normalizeRow(row):
    sum = reduce(lambda a,b : a+b, row)
    return [cell/sum for cell in row]

def wordcounts(targetwords, documents = None):
    """
    Given a list of words T and documents D, return a dictionary containing the
    counts of all words in T in D. If D is None, it is set to dbtoolkit.Articles()
    """
    if 'readlines' in dir(targetwords):
        targetwords = [x.strip() for x in targetwords.readlines()]

    f= dict([(x,0) for x in targetwords])
    
    for article in (documents or dbtoolkit.Articles()):
        for word in re.split("\W+", article.fulltext().lower()):
            if word in f:
                f[word] = f.get(word, 0) + 1
    return f
            

class GlobalWeight:
    """
    GlobalWeight(freq, documents)
    Based on a dictionary containing the global frequencies of the target words T and
    the documents D, calculate the information content of each word wrt D
    IC(w) = 1 - H(D|t)/H(D)
    this information is available through the function w(t)

    If the freq is a list of words without frequency information (ie not a dict), it
    runs wordcounts using the same document collection. If documents is not specified,
    it is assumened to be dbtoolkit.Articles() 
    """

    def __init__(self, freq, documents = None):
        if not toolkit.isDict(freq): freq = wordcounts(freq, documents)
        self.G = {}
        self._calc(freq, documents)

    def _calc(self, freq, documents):
        G = self.G
        ndoc = 0

        toolkit.warn("Computing global weights...")
        for article in (documents or dbtoolkit.Articles()):
            ticker.tick()
            ndoc += 1
            lf = {}
            str = article.fulltext()
            if type <> 4: str = str.lower()
            for word in re.split(type==4 and "\s+" or "\W+",str):
                if type==4: word = toolkit.wplToWc(word, lax=True)
                if word in freq:
                    lf[word] = lf.get(word,0) + 1

            for word, lf in lf.items():
                #print "word %s : " % word,
                pdw = 1.0 * lf / freq[word]
                #print "p(d|w) = %1.3f, " % pdw,
                DG = pdw * log2(pdw)
                #print "DG = %1.3f, " % DG,
                G[word] = G.get(word,0) + DG
                #print "G is now %1.8f" % G[word]
        self.HD = log2(ndoc)

    def __contains__(self, term):
        return term in G

    def __getitem__(self, term):
        if term in G:
            return self.w(term)
        else:
            raise KeyError(term)

    def w(self,t):
        return 1 + (self.G[t] / self.HD)

if __name__=='__main__':
    words = open(sys.argv[1]).readlines()
    type = len(sys.argv) > 2 and int(sys.argv[2]) or 2
    sep = None
    if '\t' in words[0]: sep='\t'
    if '|' in words[0]: sep='|'
    if sep:
        wordstrs = words
        words = {}
        for s in wordstrs:
            word, count = s.split(sep)
            words[word] = int(count)
            #words.append(word)
    
    g = GlobalWeight(words, dbtoolkit.Articles(cache_aidlist = 1, type=type, tick=True))
    items =toolkit.sortByValue(g.G, reverse=1)
    for x in g.G.keys():
        print "%s\t%s" % (x, g.w(x))
