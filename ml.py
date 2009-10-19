import codingjob, mlfeature, collections, toolkit

class MachineLearner(object):
    """
    Class to conduct Machine Learning tasks, such as training, testing, and n-fold train-test runs.

    This class is a 'configuration class', ie it exists mainly to connect various parts together, such as:
    - codingjob.py objects that are the source data
    - mlalgo.py objects to conduct the machine learning
    """
    
    def __init__(self, units=None, field=None, featureset=None, algorithm=None,
                 testunits=None, fieldname=None, targetfunc = None):
        self.units = set(units or [])
        self.field = field
        self.featureset = featureset or mlfeature.FeatureSet()
        self.algorithm = algorithm
        self.testunits = set(testunits or [])
        self.fieldname = fieldname
        self.targetfunc = targetfunc

    def isUnitLevel(self):
        if not self.field: return None
        return not self.field.schema.articleschema
        
    def addData(self, data, test=False, unitLevel=True):
        job = getJob(data)        
        if (not self.field) and self.fieldname:
            self.setField(job, unitLevel)
        self._check(getJob(data))
        d = self.testunits if test else self.units
        d |= set(getUnits(self.isUnitLevel(), data))


    def setField(self, job, unitLevel=True):
        schema = job.unitSchema if unitLevel else job.articleSchema
        self.field = schema.getField(self.fieldname)
        
    def _check(self, job):
        if not self.field:
            raise Exception("Cannot add data before coding field is selected")
        schema = job.unitSchema if self.isUnitLevel() else job.articleSchema
        if not schema.getField(self.field.fieldname):
            raise Exception("Job does not have field %s in schema %s" % (self.field.fieldname, schema))
        
    def getTargetClass(self, unit):
        fn = self.field.fieldname if self.field else self.fieldname
        result =  str(unit.getValue(fn))
        if self.targetfunc:
            result = self.targetfunc(result)
        return result
                    
    def train(self, units=None):
        if not units: units = self.units
        return self.algorithm.train(units, self.featureset, self.getTargetClass)
    def predict(self, model, units=None):
        if not units: units = self.testunits or self.units
        return self.algorithm.predict(units, self.featureset, model)
    def confusion(self, trainunits=None, testunits=None):
        if not trainunits: trainunits = self.units
        if not testunits: testunits = self.testunits or self.units
        model = self.train(units=trainunits)
        result = collections.defaultdict(int)
        for u, c in self.predict(model, units=testunits):
            c2 = self.getTargetClass(u)
            result[c2, c] += 1
        return result
    def nfold(self, n=10):
        for i in range(n):
            toolkit.ticker.warn("Iteration %i" % (i+1))
            train = []
            test = []
            for j, u in enumerate(self.units):
                if (j % n) == i:
                    test.append(u)
                else:
                    train.append(u)
            yield self.confusion(train, test)
    def combinedNFold(self, n=10):
        tc = {}
        for c in self.nfold():
            tc = addCm(c, tc)
        return tc
        

def getUnits(unitlevel, *data):
    for d in data:
        if type(d) == codingjob.CodingJob:
            for u in getUnits(unitlevel, *d.sets):
                yield u
        elif type(d) == codingjob.CodingJobSet:
            for u in getUnits(unitlevel, *d.articles):
                yield u
        elif type(d) == codingjob.CodedArticle:
            if unitlevel:
                for u in d.sentences:
                    yield u
            else:
                yield d
        elif type(d) == codingjob.CodedSentence:
            if unitlevel:
                yield d
            else:
                yield d.ca


    
def accuracy(cm):
    pos = 0
    tot = 0
    for (a,b), c in cm.items():
        if a == b:
            pos += c
        tot += c
    return float(pos) / tot
        
def addCm(cm1, cm2):
    keys = set(cm1.keys()) | set(cm2.keys())
    result = {}
    for key in keys:
        result[key] = cm1.get(key, 0) + cm2.get(key, 0)
    return result
        
        
    
def getJob(data):
    if type(data) == codingjob.CodingJobSet:
        return data.job
    if type(data) == codingjob.CodedArticle:
        return data.set.job
    if type(data) <> codingjob.CodingJob:
        raise Exception("Cannot adapt %r to CodingJob" % data)
    return data

if __name__ == '__main__':
    import dbtoolkit, mlalgo
    db = dbtoolkit.amcatDB()

    fn, unit = "irrelevant", False
    fn, unit = "topic", False

    
    ml = MachineLearner()
    ml.fieldname = fn
    ml.algorithm = mlalgo.MaxentAlgorithm()
    ml.addData(codingjob.CodingJob(db, 2499), unitLevel=unit)
    print "%i articles loaded" % len(ml.units)
    ml.featureset.features += list(mlfeature.getWordFeatures(ml.units, 2))

    print "Total: %1.0f%%" % (accuracy(ml.combinedNFold())*100)
        
    ml.targetfunc = lambda topic: str(topic)[:-2]

    print "Total supertopic: %1.0f%%" % (accuracy(ml.combinedNFold())*100)

    
    
