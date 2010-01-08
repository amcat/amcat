import toolkit
import collections
avg = toolkit.average

def safediv(a, b):
    if not b: return None
    return float(a)/b

class Scorer(object):
    def __init__(self):
       self._tp = 0
       self._tn = 0
       self._fp = 0
       self._fn = 0

    def fp(self):
        self._fp +=1

    def fn(self):
        self._fn +=1

    def tp(self):
        self._tp +=1

    def tn(self):
        self._tn +=1

    def n(self):
        return self._tp + self._fn

#    def accuracy(self):
#        return float(self._tp + self._tn) / (self._tp + self._fp + self._tn + self._fn)

    def recall(self):
        return safediv(self._tp, self._tp + self._fn)

    def precision(self):
        return safediv(self._tp, self._tp + self._fp)

    def fscore(self):
        p = self.precision() or 0
        r = self.recall() or 0
        return safediv(2*p*r, p+r) or 0

class Scorers(object):
    def __init__(self, tags="dummy"):
        self.scorers = collections.defaultdict(Scorer)
        self.confmatrix = collections.defaultdict(int) # {true, pred : n}
        self._nok = 0
        self._n = 0

    def observe(self, correct, guess):
        self._n += 1
        self.confmatrix[correct, guess] += 1

        if correct == guess:
            self.scorers[correct].tp()
            self._nok += 1
        else:
            self.scorers[correct].fn()
            self.scorers[guess].fp()

    def observeUnit(self, unit, correct, guess):
        # to allow use as sink
        self.observe(correct, guess)

    def n(self, tag=None):
        if tag:
            return self.scorers[tag].n()
        else:
            return self._n
    def accuracy(self):
        return safediv(self._nok, self._n)
    def recall(self, tag):
        return self.scorers[tag].recall()
    def precision(self, tag):
        return self.scorers[tag].precision()
    def fscore(self, tag):
        return self.scorers[tag].fscore()
    def avgrecall(self, omit=None):
        return avg([self.scorers[tag].recall() for tag in self.scorers if tag <> omit])
    def avgprecision(self, omit=None):
        return avg([self.scorers[tag].precision() for tag in self.scorers if tag <> omit])
    def avgfscore(self, omit=None):
        return avg([self.scorers[tag].fscore() for tag in self.scorers if tag <> omit])

    def confmstr(self):
        str = "Act   Pred\t%s\t    N\n"% ("\t".join("%10s" % t for t in self.scorers))
        for act in self.scorers:
            str += "%-10s\t%s\t%5i\n" % (act, "\t".join(
                "%10i" % self.confmatrix[act, p] for p in self.scorers),
                self.scorers[act].n())
        return str


if __name__ == '__main__':
    tags = ["min", "neut", "plus"]
    s = Scorers(tags)
    data = [[ 39, 82, 55],
            [135,567,245],
            [ 30, 78,121]] # set a / lonneke

    data = [[ 12,157,  7],
            [  9,920, 18],
            [  3,198, 28]] # set tree_g
    
    for correct, row in zip(tags, data):
        for guess, f in zip(tags, row):
            for i in range(f):
                s.observe(correct, guess)

    print "Precision\tRecall\tF-measure\tClass"
    for tag in tags:
        data = [s.precision(tag), s.recall(tag), s.fscore(tag)]
        print "%s\t%s" % (toolkit.join(data, fmt="%1.3f"), tag)
    
    data = s.avgfscore("neut"), s.avgfscore(), s.avgrecall("neut"), s.accuracy() * 100
    print "\nF\tf\tr\tacc"
    print toolkit.join(data, fmt="%1.2f")


    # Expected output for a:
    #Precision       Recall  F-measure       Class
    #0.191   0.222   0.205   min
    #0.780   0.599   0.677   neut
    #0.287   0.528   0.372   plus
    #
    #F       f       r       acc
    #0.29    0.42    0.37    53.77

    # Expected output for tree_g:
    #Precision       Recall  F-measure       Class
    #0.500   0.068   0.120   min
    #0.722   0.971   0.828   neut
    #0.528   0.122   0.199   plus
    #
    #F       f       r       acc
    #0.16    0.38    0.10    71.01
    
