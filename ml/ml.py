import collections
import random
import itertools, os, math
from functools import partial
from itertools import izip, ifilter



from amcat.model.coding import codingjob, codedsentence, codedarticle
from amcat.ml import mlfeature
from amcat.tools import toolkit
from amcat.tools.stat import fscore
from amcat.tools.table import table3

class Match(object):
    def __init__(self, predictions, unit=None, actual=None, context=None):
        self.unit = unit
        if isinstance(predictions,  dict):
            predictions = toolkit.sortByValue(predictions, reverse=True)
        elif type(predictions) <> (list, tuple):
            predictions = ((predictions, None), )
        self.predictions = predictions # [(top, conf), (nr2, conf), ...]
        self.actual = actual
        self.context = context
    def getPrediction(self):
        return str(self.predictions[0][0])
    def getConfidence(self):
        return str(self.predictions[0][1])
    def getActual(self):
        return str(self.actual)
    def getActualPosition(self):
        act = self.getActual()
        for i, pred in enumerate(self.predictions):
            if str(pred[0]) == act:
                return i
        return None

    def toList(self, npreds=5, meta=True):

        data = [self.unit, str(self.context), self.getActual()] if meta else []
        ap = self.getActualPosition()
        if ap is None: ap = 9999
        data += [ap]
        for i in range(npreds):
            if i >= len(self.predictions): data += ["", "0.0"]
            else: data += [str(self.predictions[i][0]), "%1.3f" % self.predictions[i][1]]
        return data
    def getConfidence(self):
        return self.predictions[0][1]

class MatchesTable(table3.ObjectTable):
    def __init__(self, matches):
        if type(matches) not in (list, tuple): matches = list(matches)
        matches = [m for m in matches if m.actual is not None]
        table3.ObjectTable.__init__(self, rows=matches)
        self.addColumn(table3.ObjectColumn("unit", lambda m:m.unit.id))
        self.addColumn(table3.ObjectColumn("context", lambda m:str(m.context)))
        self.addColumn(table3.ObjectColumn("actual", lambda m:m.getActual()))
        self.addColumn(table3.ObjectColumn("actualpos", lambda m:m.getActualPosition()))
        def getPrediction(match, i, j):
            if i >= len(match.predictions): return None
            return match.predictions[i][j]
        for i in range(0,6):
            self.addColumn(table3.ObjectColumn("pred%i"%i, partial(getPrediction, i=i, j=0)))
            self.addColumn(table3.ObjectColumn("conf%i"%i, partial(getPrediction, i=i, j=1)))


class MachineLearner(object):
    """
    Class to conduct Machine Learning tasks, such as training, testing, and n-fold train-test runs.

    This class is a 'configuration class', ie it exists mainly to connect various parts together, such as:
    - codingjob.py objects that are the source data
    - mlalgo.py objects to conduct the machine learning
    """
    
    
    def __init__(self, units=None, featureset=None, algorithm=None, targetFunc=None, debughook=None):
        self.units = set(units or [])
        self.featureset = featureset or mlfeature.FeatureSet()
        self.algorithm = algorithm
        self.targetFunc = targetFunc
        self.model = None
        self.debughook = debughook

    def debug(self, msg):
        if self.debughook:
            try:
                self.debughook(msg)
            except Exception, e:
                toolkit.warn("Exception on debugging!\nMsg: %r\nError: %s" % (msg, e))
                
        
    def addData(self, data, unitlevel=True):
        self.units |= set(getUnits(unitlevel, data))

    def getTargetClass(self, unit):        
        result =  str(unit.values[self.field.fieldname])
        return result

    def getUnits(self, units_or_filter=None):
        if callable(units_or_filter):
            units = ifilter(units_or_filter, self.units)
        elif units_or_filter:
            units = units_or_filter
        else:
            units = self.units
        if self.targetFunc:
            units = ifilter(partial(hasAnnotation, targetfunc=self.targetFunc), units)

	###### HACK ########
	#units = list(units)[:100]
	    
        return units
    def train(self, data=None):
        units = list(self.getUnits(data))
        self.debug("Training on %i units" % len(units))
                
        self.featureset.start(units)
        self.model = self.algorithm.train(units, self.featureset, self.targetFunc)
        return self.model
    def predict(self, model=None, data=None):
        units = list(self.getUnits(data))
        self.debug("Predicting on %i units" % len(units))
        self.featureset.start(units)
        if not model: model = self.model
        for match in self.algorithm.predict(units, self.featureset, model):
            try:
                match.actual = self.targetFunc(match.unit)
            except:
                match.actual = "?"
            yield match
    def run(self, trainunits_or_filter, testunits_or_filter):
        self.train(data=trainunits_or_filter)
        return self.predict(data=testunits_or_filter)
       
    def nfold(self, **kargs):
        for i, (train, test) in enumerate(self.nfolddata(**kargs)):
            for match in self.run(train, test):
                match.context = i
                yield match
                
    def nfoldacc(self, **kargs):
        tags = set(self.targetFunc(u) for u in self.units)
        s = fscore.Scorers(tags)
        for match in self.nfold(**kargs):
            s.observe(match.getActual(),match.getPrediction())
        return s.accuracy()

    def nfolddata(self, units_or_filter=None, n=10, shuffle=True):
        units = self.getUnits(units_or_filter)
        units = list(ifilter(partial(hasAnnotation, targetfunc=self.targetFunc), units))
        if shuffle: random.shuffle(units)
        self.debug("Creating %i folds from %i units" % (n, len(units)))
        for i in range(n):
            train = []
            test = []
            for j, u in enumerate(units):
                if (j % n) == i:
                    test.append(u)
                else:
                    train.append(u)
            self.debug("Fold %i, #train=%i, #test=%i" % (i, len(train), len(test)))
            yield train, test

    def statisticsTable(self):
        t = table3.ListTable(colnames=["Item", "Name", "N", "N (coded)"])
        t.addRow("Algorithm", self.algorithm)
        t.addRow("Feature", "Features", len(self.featureset.features))
        t.addRow("Units", "?", len(self.units))
        return t
       
def hasAnnotation(unit, targetfunc):
    if not targetfunc: return True
    if type(unit) not in (codedarticle.CodedArticle, codedsentence.CodedSentence): return True
    return targetfunc(unit) is not None
            
def getUnits(unitlevel, *data):
    for d in data:
        if type(d) == codingjob.CodingJob:
            if unitlevel:
                for u in codingjob.getCodedSentencesFromCodingjobs([d]):
                    yield u
            else:
                for u in codingjob.getCodedArticlesFromCodingjobs([d]):
                    yield u
        elif type(d) == codingjob.CodingJobSet:
            for u in getUnits(unitlevel, *d.articles):
                yield u
        elif type(d) == codedarticle.CodedArticle:
            if unitlevel:
                for u in d.sentences:
                    yield u
            else:
                yield d
        elif type(d) == codedsentence.CodedSentence:
            if unitlevel:
                yield d
            else:
                yield d.ca

def fieldTargetFunc(fieldname, typefunc=str):
    print fieldname, typefunc
    return lambda unit : typefunc(unit.values[fieldname])

def scorers(matches):
    s = fscore.Scorers()
    for m in matches:
        s.observe(m.getActual(), m.getPrediction())
    return s


legacy = {"accuracy" : "a", "fscore" : "f", "both" : "af"}

METRICS = {
    'a' : (lambda s:s.accuracy(), 'Acc', '%1.2f'),
    'f' : (lambda s:s.avgfscore(), 'F1', '%1.2f'),
    'p' : (lambda s:s.avgprecision(), 'Pr', '%1.2f'),
    'r' : (lambda s:s.avgrecall(), 'Re', '%1.2f'),
    'n' : (lambda s:s.n(), 'N', '%i'),
}

def accuracy(matches_or_scorers, metrics='a', string=False, format=False, result='legacy'): # may be 'accuracy', 'fscore', 'both', or 'scorers'
    if type(matches_or_scorers) == fscore.Scorers:
        s = matches_or_scorers
    else:
        s = scorers(matches_or_scorers)
    if result and not metrics: metrics = result
    metrics = legacy.get(metrics, metrics)

    funcs, labels, fmts = [[METRICS[m][i] for m in metrics] for i in (0,1,2)]

    result = [f(s) for f in funcs]
    if string or format:
        result = [(f%r if (r is not None) else "-") for (f,r) in zip(fmts, result)]
    if string:
        return ", ".join("%s: %s" % (l, r) for (l,r) in zip(labels, result))
    return result

def accuracytable(data, metrics='a', names=None, colnames=None):
    data = data.iteritems() if type(data) == dict else zip(names, data)
    result = table3.ListTable()
    for name, matches in data:
        result.addRow(name, *accuracy(matches, metrics, format=True))
    result.colnames = ['Name'] + [METRICS[m][1] for m in metrics]
    if colnames:
        for i, name in enumerate(colnames):
            result.colnames[i] = name
    return result
    

def topN(matches, n=10):
    nok = 0
    for m in matches:
        p = m.getActualPosition()
        if p is not None and p < n:
            nok += 1
    return float(nok) / len(matches)

def confidenceDistribution(matchers, nbins=10):
    result = [fscore.Scorers() for dummy in range(nbins)] #float -> scorer
    for m in matchers:
        c = m.getConfidence()
        bin = min(nbins-1, int(math.floor(c*10)))
        result[bin].observe(m.getActual(), m.getPrediction())
    return result

if __name__ == '__main__':
    import dbtoolkit, mlalgo, indexfeature, amcatxapian
    db = dbtoolkit.amcatDB()
    cj = codingjob.Codingjob(db, 268)
    index = amcatxapian.Index("/home/wva/tmp/xapian-test", db) # index of codingjob 268

    ml = MachineLearner()
    ml.addData(cj)
    ml.units = list(ml.units)[:50]
    ml.targetFunc = fieldTargetFunc("subject")
    ml.featureset.features += list(indexfeature.getWordFeatures(index, 5))
    ml.algorithm = mlalgo.MetaAlgorithm(mlalgo.MaxentAlgorithm(),
                                        mlalgo.LibSVMAlgorithm("RBF", C=1E5, gamma=1E-3, probability=True))
    #ml.algorithm = mlalgo.MaxentAlgorithm()
    ml.train()
    matches = list(ml.predict())
    
    toolkit.warn("accuracy: %s" % (accuracy(matches, result='both'),))

    import amcatr
    frame = amcatr.table2RFrame(MatchesTable(matches))
    amcatr.call("/home/wva/tmp/test.r", "go", frame)
    
