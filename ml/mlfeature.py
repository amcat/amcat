import re, codingjob, toolkit

class FeatureSet(object):
    """
    Class representing a collection of features. The set as a whole
    needs to be persisted because feature numbers are generally
    important
    """

    def __init__(self, offset=1):
        self.features = [] 
        self.memo = None # dict reset for each unit to allow inter-feature optimization
        self.permanentMemo = {} # dict persistent (within a session) to allow inter-unit optimization
        self.offset = offset

    def start(self, units):
        self.permanentMemo = {}
        for f in self.features:
            f.start(units, self)
    
    def getScores(self, unit):
        """ yields fno, score pairs"""
        self.memo = {}
        for f in self.features: f.init(unit, self)
        for f in self.features:
            s = f.score(unit, self)
            if s:
                yield self.getFeatureNumber(f), s
        self.memo = None
    def getFeatureNumber(self, feature):
        return self.features.index(feature) + self.offset # inefficient!
    def getDict(self, unit):
        return dict(self.getScores(unit))

class Feature(object):
    """
    Class representing a feature, essentially a function capable
    of converting a unit into a value. Subclasses must override
    score and may provide an init
    """
    def start(self, units, featureset):
        """
        Called before iterating over the units to allow optimization
        featureset is given for access to memos
        """
        pass
    def init(self, unit, featureset):
        """
        Called at the beginning of each unit to allow initialization
        featureset is given for access to memos
        """
        pass
    def score(self, unit, featureset):
        """
        Called for each unit to get the feature value.
        featureset is given for access to memos.
        """
        abstract

class WordFeature(Feature):
    def __init__(self, word, case=False):
        self.case = case
        if not self.case: word = word.lower()
        self.word = word
        self.wckey = "WordFeature;case=%s;wordcounts" % self.case
        self.counterkey = "WordFeature;case=%s;counter" % self.case
    def score(self, unit, fs):
        return fs.memo[self.wckey].get(fs.getFeatureNumber(self),0)
    def init(self, unit, fs):
        import ccount
        if self.wckey in fs.memo: return
        if self.counterkey not in fs.permanentMemo:
            words = {}
            for f in fs.features:
                if type(f) == WordFeature and f.case == self.case:
                    words[f.word] =  fs.getFeatureNumber(f)
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
    __repr__ = __str__
    

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
    import ctokenizer
    text = getText(unit)
    if not case: text = text.lower()
    text = ctokenizer.tokenize(text)
    return text.split(" ")
    
if __name__ == '__main__':
    fs = FeatureSet()
    text = "Er staat een Boom in de wei tussen de apenboom en de paardenbloem. Boom, zei de bloem"
    fs.features += list(getWordFeatures([text], 1))
    print ",".join(map(str, fs.features))
    for i, s in fs.getScores(text):
        print i, fs.features[i], s


