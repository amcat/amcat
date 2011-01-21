from amcat.tools import toolkit
import math, os, itertools, collections
from amcat.ml.ml import Match
#import svm

#svm.svmc.svm_set_quiet()
        
class Algorithm(object):
    """
    Class/Interface representing the various ML algorithms
    """
    
    def train(self, units, featureset, targetfunc):
        """
        Trains the machine learner with the given:
        - units: codinjob::CodedArticle -or- codingjob::Sentence
        - features: mlfeature::FeatureSet
        - targetfunc: a function of unit --> class
        Returns a model blob
        """
        abstract

    def predict(self, units, featureset, model):
        """
        Predicts the class of the units given the featureset and model
        - units: codinjob::CodedArticle -or- codingjob::Sentence
        - features: mlfeature::FeatureSet
        - model: a blob (as returned by train)
        Yields Match objects
        """
        abstract

class MetaAlgorithm(Algorithm):
    def __init__(self, *algos):
        self.algos = algos
    def train(self, units, featureset, targetfunc):
        return tuple(algo.train(units, featureset, targetfunc)
                     for algo in self.algos)
    def predict(self, units, featureset, model):
        predictions = tuple(algo.predict(units, featureset, model[i])
                            for i, algo in enumerate(self.algos))
        for matches in itertools.izip(*predictions):
            predictions = collections.defaultdict(float) # class -> sumprob
            for i, match in enumerate(matches):
                for cl, pr in match.predictions:
                    predictions[cl] += pr
            for k in predictions: predictions[k] /= len(matches)
            yield Match(predictions, match.unit, match.actual, match.context)

                

class LibSVMAlgorithm(Algorithm):
    def __init__(self, kernel, **params):
        if type(kernel) == str:
            kernel = svm.__dict__[kernel]
        self.param = svm.svm_parameter(kernel_type=kernel, **params)
        self.probabilities = params.get("probability", False)
    def train(self, units, featureset, targetfunc):
        labels = map(targetfunc, units)
        samples = map(featureset.getDict, units)
        prob = svm.svm_problem(labels, samples)
        return svm.svm_model(prob, self.param)
    def predict(self, units, featureset, model):
        for u in units:
            features = featureset.getDict(u)
            if self.probabilities:
                cls, pred = model.predict_probability(features)
            else:
                pred = model.predict(features)
            yield Match(pred, u)
        
def getFeatures(unit, featureset):
    return dict((k+1,v) for (k,v,) in featureset.getScores(unit))
    
class FeatureFileAlgorithm(Algorithm):
    """
    Base class for Algorithms that work by writing a feature file and
    calling an external program to conduct the training/predicting
    """

    def __init__(self, trainprogram=None, testprogram=None, name="algo"):
        """optional trainprogram and testprogram for base getmodel/dopredict implementation
        optional name is used for descriptive file name and str()"""
        self.name = name or self.__class__.__name__
        self.trainprogram = trainprogram
        self.testprogram = testprogram

    def writeUnitFeatures(self, unit, featureset, file, targetfunc=None):
        "return None, write features to file"
        abstract
    def getPrediction(self, line):
        "return prediction (class or class:probability dict) based on output line"
        abstract
        
    def train(self, units, featureset, targetfunc):
        "Train the model by writing the feature file and calling getModel"
        f = self._writeFeatures(units, featureset, targetfunc)
        m = self.getModel(f)
        os.remove(f)
        return m    
    def getModel(self, file):
        """return Model object (opaque).
        Base implementation executes trainprogram with input and model output filename"""
        
        if not self.trainprogram:
            raise Exception("Base getModel implementation requires trainprogram be set for %s" % self.name)
        mfn = toolkit.tempfilename(prefix="ml-%s-model-" % self.name)
        CMD = self.trainprogram % dict(model=mfn, input=file)
        toolkit.execute(CMD)
        model = open(mfn).read()
        os.remove(mfn)
        return model
    
    def predict(self, units, featureset, model):
        "Predict units by writing the feature and model file and calling doPredict"
        units = list(units)
        f = self._writeFeatures(units, featureset)
        mfn = toolkit.tempfilename("ml-model")
        m = open(mfn, 'w')
        m.write(model)
        m.close()
        for u, match in zip(units, self.doPredict(f, mfn)):
            match.unit = u
            yield match
        os.remove(mfn)
        os.remove(f)
    def doPredict(self, fn, mfn):
        """yield Match objects from the feature and model files (without unit)
        Base implementation calls testprogram and calls getPrediction on each line
        from the standard output"""
        outfn = toolkit.tempfilename(prefix="ml-%s-pred-" % self.name)
        CMD = self.testprogram % dict(model = mfn, input=fn, pred=outfn)
        o, e = toolkit.execute(CMD)
        if e: raise Exception("%s Exception!\nCMD=%r\n%s" % (self.name, CMD, e))
        predictions = map(self.getPrediction, open(outfn))
        os.remove(outfn)
        return predictions
    
    def _writeFeatures(self, units, featureset, targetfunc=None):
        "Write the feature file by calling abstract writeUnitFeatures on each unit"
        tmpfn = toolkit.tempfilename(prefix="ml-features-")
        tmp = open(tmpfn, 'w')
        hasunits = False
        for u in units:
            self.writeUnitFeatures(u, featureset, tmp, targetfunc)
            hasunits = True
        if not hasunits: raise Exception("No units given for featurefile")
        return tmpfn
    def __str__(self): return self.name
    def __repr__(self): return "FileAlgorithm(%s)" % self.name
    
MAXENT_TRAIN = "maxent -b -m%(model)s %(input)s"
MAXENT_PREDICT =  "maxent -b -p --detail -m%(model)s -o%(pred)s %(input)s"

class MaxentAlgorithm(FeatureFileAlgorithm):
    def __init__(self):
        FeatureFileAlgorithm.__init__(self, MAXENT_TRAIN, MAXENT_PREDICT)
    def writeUnitFeatures(self, unit, featureset, file, targetfunc=None):
        "write line with: CLASS (FEATURENO:FEATUREVAL)*"
        if targetfunc:
            file.write(str(targetfunc(unit)))
            #print str(targetfunc(unit)),
        else:
            file.write("X")
        for i, s in featureset.getScores(unit):
            if s:
                file.write(" %i:%s" % (i, s))
                #print "%i:%s" % (i, s),
                
        file.write("\n")
        #print
    def getPrediction(self, line):
        # convert c1 \t conf1 \t c2 \t conf2 to dict using ::2 stepped slicing
        return Match(dict(zip(line.split()[::2], map(float, line.split()[1::2]))))

SVM_TRAIN_TEMPLATE = "svm_multiclass_learn %s %%(input)s %%(model)s"
SVM_PREDICT =  "svm_multiclass_classify %(input)s %(model)s %(pred)s"

class SVMAlgorithm(FeatureFileAlgorithm):
    def __init__(self, **kerneloptions):
        if "c" not in kerneloptions: kerneloptions["c"] = "1.0"
        optionstr = " ".join("-%s %s" % kv for kv in kerneloptions.items())
        FeatureFileAlgorithm.__init__(self, SVM_TRAIN_TEMPLATE % optionstr, SVM_PREDICT)
        self.classes = {} # class to 1-based index
        self.inverse = [] # index-1 to class (-1 because svm wants 1-based indexing)
    def writeUnitFeatures(self, unit, featureset, file, targetfunc=None):
        if targetfunc:
            c = str(targetfunc(unit))
            if c not in self.classes:
                self.inverse.append(c)
                self.classes[c] = len(self.inverse)
            file.write(str(self.classes[c]))
        else:
            file.write("1")
        for i, s in featureset.getScores(unit):
            if s:
                file.write(" %i:%s" % (i+1, s)) # +1 because feature nums for SVM >= 1
        file.write("\n")
    def getPrediction(self, line):
        confs = map(float, line.split()[1:])
        s = sum(map(math.exp, confs))
        confs = map(lambda x : math.exp(x) / s, confs)
        pred = dict(zip(self.inverse, confs))
        return Match(pred)

def flt(x):
    if x is None: return "-"
    return "%1.2f" % x

ALGORITHM_FACTORIES = {
    "maxent":        lambda : MaxentAlgorithm(),
    "svm" :          lambda : SVMAlgorithm(),
    "libsvm_rbf":    lambda : LibSVMAlgorithm("RBF", C=1E5, gamma=1E-3, probability=True),
    "libsvm_linear": lambda : LibSVMAlgorithm("LINEAR", C=10, probability=True),
    "combined":      lambda : MetaAlgorithm(ALGORITHM_FACTORIES["maxent"](), ALGORITHM_FACTORIES["libsvm_rbf"]()),
}
    
if __name__ == '__main__':
    test = {
        "vanavond wordt het regenachtig" : 1,
        "het wordt vanavond alweer regenachtig" : 2,
        "wanneer gaan jullie naar huis?" : 2,
        "vanavond wordt het huis" : 2,
        "vanavond wordt het niks" : 1,
        "niks is geen excuus" : 1,
        "tsja vanavond wordt het regenachtig" : 1,
        "tsja het wordt vanavond alweer regenachtig" : 2,
        "tsja wanneer gaan jullie naar huis?" : 2,
        "tsja vanavond wordt het huis" : 2,
        "tsja vanavond wordt het niks" : 1,
        "tsja niks is geen excuus" : 1,
        "" : 1,
        }
    from mlfeature import *
    fs = FeatureSet()
    fs.features += list(getWordFeatures(test.keys(), 3))
    algos = [
        LibSVMAlgorithm("RBF", C=1E5, gamma=1E-3, probability=True),
        LibSVMAlgorithm("LINEAR", C=10, probability=True),
        MaxentAlgorithm(),
        SVMAlgorithm(t=1,d=3),
        MetaAlgorithm(MaxentAlgorithm(), SVMAlgorithm(t=1,d=3)),
        ]

    predictions = [list(algo.predict(test.keys(), fs, algo.train(test.keys(), fs, test.get)))
                   for algo in algos]
    for i, (unit, cls) in enumerate(test.items()):
        print "%45s %s %s" % (unit, cls, " ".join("%s %s" % (p[i].getPrediction(), flt(p[i].getConfidence())) for p in predictions))

        
