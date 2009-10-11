import toolkit

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
        Yields unit, class pairs
        """
        abstract

class FeatureFileAlgorithm(Algorithm):
    """
    Base class for Algorithms that work by writing a feature file and
    calling an external program to conduct the training/predicting
    """

    def writeUnitFeatures(self, unit, featureset, file, targetfunc=None):
        "return None, write features to file"
        abstract
    def getModel(self, file):
        "return Model blob"
        abstract
    def doPredict(self, file, model):
        "yield predictions"
        abstract
        

    def writeFeatures(self, units, featureset, targetfunc=None):
        tmpfn = toolkit.tempfilename(prefix="ml-features-")
        tmp = open(tmpfn, 'w')
        #print "Writing features to %s" % tmpfn
        for u in units:
            self.writeUnitFeatures(u, featureset, tmp, targetfunc)
        return tmpfn

    def train(self, units, featureset, targetfunc):
        f = self.writeFeatures(units, featureset, targetfunc)
        m = self.getModel(f)
        return m

    def predict(self, units, featureset, model):
        units = list(units)
        f = self.writeFeatures(units, featureset)
        mfn = toolkit.tempfilename("ml-model")
        m = open(mfn, 'w')
        m.write(model)
        m.close()

        for u, p in zip(units, self.doPredict(f, mfn)):
            yield u, p

MAXENT_TRAIN = "maxent -b -m%(model)s %(input)s"
MAXENT_PREDICT =  "maxent -b -p -m%(model)s -o%(pred)s %(input)s"

class MaxentAlgorithm(FeatureFileAlgorithm):
    def writeUnitFeatures(self, unit, featureset, file, targetfunc=None):
        if targetfunc:
            file.write(str(targetfunc(unit)))
        else:
            file.write("X")
        for i, s in featureset.getScores(unit):
            if s:
                file.write(" %i:%s" % (i, s))
        file.write("\n")
    def getModel(self, fn):
        mfn = toolkit.tempfilename(prefix="ml-maxent-model-")
        #print "Writing model to %s" % mfn
        CMD = MAXENT_TRAIN % dict(model=mfn, input=fn)
        toolkit.execute(CMD)
        model = open(mfn).read()
        return model
    def doPredict(self, fn, mfn):
        outfn = toolkit.tempfilename(prefix="ml-maxent-pred-")
        CMD = MAXENT_PREDICT % dict(model = mfn, input=fn, pred=outfn)
        o, e = toolkit.execute(CMD)
        if e: raise Exception("Maxent Exception!\nCMD=%r\n%s" % (CMD, e))
        for line in open(outfn):
            yield line.strip()

if __name__ == '__main__':
    
    test = {
        "vanavond wordt het regenachtig" : "A",
        "het wordt vanavond alweer regenachtig" : "B",
        "wanneer gaan jullie naar huis?" : "B",
        "vanavond wordt het huis" : "B",
        "vanavond wordt het niks" : "A",
        "niks is geen excuus" : "A"
        }

    from mlfeature import *
    fs = FeatureSet()
    fs.features += list(getWordFeatures(test.keys(), 2))
    print ",".join(map(str, fs.features))
        
                
    a = MaxentAlgorithm()
    m = a.train(test.keys(), fs, test.get)

    for u, c in a.predict(test.keys(), fs, m):
        print "%40s" % u, c, test.get(u)

        
