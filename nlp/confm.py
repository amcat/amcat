"""
Toolkit to generate confusion matrixes and statistics from output files

Usage:    $ Confm.py outputfile originalfile

          >>> c = confm(outputfile, originalfile)
          >>> stats(c)
"""

class ConfusionMatrix:
    
    def __init__(this):
        this.matrix = {}

    def add(this, true, pred):
        if not true in this.matrix: this.matrix[true] = {}
        this.matrix[true][pred] = this.matrix[true].get(pred, 0) + 1        

    def __str__(this):
        """
        Generates a slightly better looking matrix from the dict of dicts
        """
        result = ""
        result += "          |       predicted         |\n"
        
        result += "true      | %s |\n" % " | ".join(map(_sol, this.matrix.keys()))
        result += "----------+------------+------------+\n"
        for true in this.matrix.keys():
            result += "%s         | %s |\n" % (true, " | ".join(map(lambda x:_sol(this.matrix[true][x]), this.matrix.keys())))
        return result

    def accuracy(this):
        t = 0.0; f = 0.0;
        for true in this.matrix.keys():
            for pred, count in this.matrix[true].items():
                if pred == true: t += count
                else:            f += count
                
        return t/(t+f)

    def n(this, cl = None):
        if cl == None: cls = this.matrix.keys()
        else: cls = [cl]
        sum = 0
        for cl in cls:
            for x, c in this.matrix[cl].items():
                sum += c

        return sum
            

    def precision(this, cl):
        tp = 0.0; fp = 0.0;
        for true in this.matrix.keys():
            if true == cl: tp += this.matrix[true][cl]
            else:          fp += this.matrix[true][cl]
                
        return tp/(tp+fp)

    def recall(this, cl):
        tp = 0.0; fn = 0.0;
        for pred in this.matrix[cl].keys():
            if pred == cl: tp += this.matrix[cl][pred]
            else:          fn += this.matrix[cl][pred]
                
        return tp/(tp+fn)

    def f1(this, cl):
        p = this.precision(cl)
        r = this.recall(cl)
        return 2*p*r / (p+r)

    def stats(this):
        result = "Total accuracy: %0.3f (n=%s)" % (this.accuracy(), this.n())
        for cl in this.matrix.keys():
            result += "\n\nFor class %s (n=%s, %0.3f%%)" % (cl, this.n(cl), (1.0 * this.n(cl) / this.n()))
            result += "\n  Precision: %0.3f" % this.precision(cl)
            result += "\n  Reacll:    %0.3f" % this.recall(cl)
            result += "\n  F1-score:  %0.3f" % this.f1(cl)

        return result
        

def _sol(s, l = 10):
    result = "%s"%s
    result += " " * (10 - len(result))
    return result
    

def readMaxent(outputfile, original):
    """
    Generates a confusion matrix from an outputfile and original file
    Assumes the first character on each line contains the class and the
    order is identical

    Outputs a dict of dicts where confm(..)[true][pred] is the number of
    cases that was predicted as 'pred' and should have been 'true'
    """
    #ASSUME #classes < 10!
    result = ConfusionMatrix()
    
    for line_pred in outputfile:
        line_true = original.readline()
        pred = int(line_pred[0])
        true = int(line_true[0])
        result.add(true, pred)
    
    return result

if __name__ == '__main__':

    import sys
    
    if len(sys.argv) <> 3:
        print __doc__
        sys.exit(1)

    outputfile = open(sys.argv[1])
    original   = open(sys.argv[2])
    matrix = readMaxent(outputfile, original)
    print matrix
    print matrix.stats()


