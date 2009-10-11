import re, codingjob, ctokenizer, toolkit, ccount

class FeatureSet(object):
    """
    Class representing a collection of features. The set as a whole
    needs to be persisted because feature numbers are generally
    important
    """

    def __init__(self):
        self.features = []
        self.memo = None
        self.permanentMemo = {}

    def reset(self):
        self.permanentMemo = {}
    
    def getScores(self, unit):
        """ yields fno, score pairs"""
        self.memo = {}
        for f in self.features: f.init(unit, self)
        for i, f in enumerate(self.features):
            s = f.score(unit, self, i)
            yield i, s
        self.memo = None
        

class Feature(object):
    """
    Class representing a feature, essentially a function capable
    of converting a unit into a value. Subclasses must override
    either score or scoreText.
    """
    def init(self, unit, featureset):
        pass
    def score(self, unit, i):
        abstract

class WordFeature(Feature):
    def __init__(self, word, case=False):
        self.case = case
        if not self.case: word = word.lower()
        self.word = word
        self.wckey = "WordFeature;case=%s;wordcounts" % self.case
        self.counterkey = "WordFeature;case=%s;counter" % self.case
    def score(self, unit, fs, i):
        return fs.memo[self.wckey].get(i,0)
    def init(self, unit, fs):
        if self.wckey in fs.memo: return
        if self.counterkey not in fs.permanentMemo:
            words = {}
            for i, f in enumerate(fs.features):
                if type(f) == WordFeature and f.case == self.case:
                    words[f.word] = i
            fs.permanentMemo[self.counterkey] = ccount.Counter(words)
        c = fs.permanentMemo[self.counterkey]
        fs.memo[self.wckey] = c.count(getText(unit), lower=not self.case)
        
    def getWordCounts(self, text):
        context = GLOBAL_CONTEXT.getContext(text)

        if key in context:
            return context[key]
        words = getWords(text)
        counts = count(words)
        context[key] = words
        return words
    def __str__(self):
        return "WordFeature(%r)" % self.word
    

def getWordFeatures(units, thres=5, case=False):
    words = {}
    for u in units:
        for w in getWords(u, case=case):
            f = words.get(w, 0)
            if f == -1: continue
            if (f+1) >= thres:
                words[w] = -1
                yield WordFeature(w, case)
            else:
                words[w] = f+1
    
def getText(unit):
    if type(unit) in (str, unicode): return unit
    if type(unit) == codingjob.CodedArticle:
        t = unit.article.getText()
        t = toolkit.stripAccents(t)
        t = t.encode('latin-1', 'replace')
        return t
    if type(unit) == codingjob.CodedSentence:
        return unit.sentence.text

def getWords(unit, case=False):
    text = getText(unit)
    if not case: text = text.lower()
    text = ctokenizer.tokenize(text)
    return text.split(" ")
    
if __name__ == '__main__':
    fs = FeatureSet()
    text = "Er staat een Boom inde wei tussen de apenboom en de paardenbloem.Boom, zei de bloem"
    fs.features += list(getWordFeatures([text], 1))
    print ",".join(map(str, fs.features))
    for i, s in fs.getScores(text):
        print i, fs.features[i], s


