import toolkit, output

def m_nominal(a,b): return int(a<>b)
def m_interval(a,b): return (a-b)**2
def m_ratio(a,b): return (float(a-b)/(a+b))**2

def trans_n(x):
    if x is None: return 0
    return len(x)
def trans_avg(x):
    if x is None: return None
    return float(sum(x)) / len(x)


class MultisetReliability:
    def __init__(self):
        self.data = toolkit.DefaultDict(list) # (unit, observer) -> value
        self.units = set()
        self.observers = set()

    def addEntry(self, unit, observer, value):
        self.data[unit, observer].append(value)
        self.units.add(unit)
        self.observers.add(observer)

    def getReliability(self, func):
        r = Reliability()
        for u in self.units:
            for o in self.observers:
                val = self.data.get((u, o))
                val = func(val)
                if val is not None:
                    r.addEntry(u,o, val)
        return r

    def fscore(self, obsa, obsb, multiset, transform=None):
        tp = 0
        fp = 0
        fn = 0
        for u in self.units:
            va = count(self.data.get((u, obsa)), transform)
            vb = count(self.data.get((u, obsb)), transform)
            values = set(va.keys()) | set(vb.keys())
            for v in values:
                ca = va[v]
                cb = vb[v]
                if not multiset:
                    ca = min(ca, 1)
                    cb = min(cb, 1)
                if ca > cb:
                    tp += cb
                    fn += ca - cb
                else:
                    tp += ca
                    fp += cb - ca
        if not (tp or fp or fn): return None, None, None
        if not tp: return 0., 0., 0.
        pr = float(tp) / (tp + fp)
        re = float(tp) / (tp + fn)
        f = 2*pr*re / (pr + re)
        return pr, re, f

    def confusion(self, observers=None):
        result = toolkit.DefaultDict(int)
        for u in self.units:
            for i, o in enumerate(self.observers):
                if observers and (o not in observers): continue
                for j, o2 in enumerate(self.observers):
                    if j <= i: continue
                    if observers and (o2 not in observers): continue
                    va = set(self.data.get((u, o), []))
                    vb = set(self.data.get((u, o2), []))
                    ad = va - vb
                    bd = vb - va
                    w = 1#1.0 / (len(ad) * len(bd))
                    for obj in ad:
                        for obj2 in bd:
                            if obj.id > obj2.id: key = obj, obj2
                            else: key = obj2, obj
                            result[key] += w
        return result
                
    
def count(seq, transform = None):
    l = toolkit.DefaultDict(int)
    if seq:
        for s in seq:
            if transform: s = transform(s)
            l[s] += 1
    return l

class Reliability:

    def __init__(self):
        self.data = {} # (unit, observer) -> value
        self.units = set()
        self.observers = set()
        self.values = set()

    def addEntry(self, unit, observer, value):
        if value is None: return
        self.data[unit, observer] = value
        self.units.add(unit)
        self.observers.add(observer)
        self.values.add(value)
        #toolkit.warn("Added %r ; %r = %r" % (unit, observer, value))

    def addRow(self, *values):
        if len(values)==1 and toolkit.isSequence(values[0], True): values = values[0]
        unit = len(self.units)
        for i, value in enumerate(values):
            self.addEntry(unit, i, value)

    def getData(self, unitname = "unit", observername = "Observer", valuename = "Value", asList = False):
        units = sorted(self.units)
        observers = sorted(self.observers)

        result = output.Table()
        if asList:
            result.addHeader(unitname, observername, valuename)
            for unit in units:
                for observer in observers:
                    if (unit, observer) in self.data:
                        result.addRow(unit, observer, self.data[unit, observer])
                
        else:
            result.addHeader(unitname, *observers)
            for unit in units:
                result.addValue(unit)
                for observer in observers:
                    result.addValue(self.data.get((unit, observer), None))
                result.newRow()
        return result
                 
            
    def getCoinTable(self, observers = None):
        if not observers: observers = self.observers
        coin = toolkit.DefaultDict(int)
        for unit in self.units:
            vals = [self.data.get((unit, observer), None) for observer in observers]


            nvalid = len([v for v in vals if v is not None])
            if nvalid <= 1: continue
                
            for i, v1 in enumerate(vals):
                if v1 is None: continue
                for j,v2 in enumerate(vals):
                    if i==j or v2 is None: continue
                    coin[v1, v2] += 1 / float(nvalid-1)

        return coin

    def getConfusion(self, obsA, obsB):
        confusion = toolkit.DefaultDict(int)
        for unit in self.units:
            valA = self.data.get((unit, obsA), None)
            valB = self.data.get((unit, obsB), None)
            confusion[valA, valB] += 1
        return confusion


    def percentage(self, obsA, obsB):
        c = self.getConfusion(obsA, obsB)
        ok, n = 0, 0
        for (a,b), count in c.items():
            if a==b: ok += count
            n += count
        if not n: return None
        return float(ok) / n
            
    

    def coinTable(self, observers = None):
        result = output.Table()
        coin = self.getCoinTable(observers)
        valist = sorted(self.values)
        result.addHeader("", *valist)
        for va in valist:
            vals = [coin[va, va2] for va2 in valist]
            result.addRow(va, *vals)
        return result

    def getValueCounts(self, observer):
        result = toolkit.DefaultDict(int)
        for unit in self.units:
            value = self.data.get((unit, observer), None)
            result[value] += 1
        return result

    def alpha(self, observers = None, metric = m_nominal, returncalc = False):
        coin = self.getCoinTable(observers)
        values = sorted(self.values)

        sums = toolkit.DefaultDict(int)
        for row in self.values:
            for column in self.values:
                sums[row] += coin[row, column]
        n = sum(sums.values())

        num, denom = 0,0
        for i, c in enumerate(values):
            for k in values[i+1:]:
                num += coin[c,k] * metric(c,k)
                denom += sums[c] * sums[k] * metric(c,k)

        if denom == 0 or n == 0: alpha = None
        else: alpha = 1 - (n-1) * float(num) / denom
        if not returncalc: return alpha

        sig = u"\N{GREEK CAPITAL LETTER SIGMA}"
        dot = u"\N{MIDDLE DOT}"
        alph = u"\N{GREEK SMALL LETTER ALPHA}"

        pre = alph + " = 1 - (n-1)"+dot
        prec0 = "   "+sig+"c "+sig+"k>c o_kc"+dot+metric.__name__+"(k,c)  "
        prec1 = sig+"c "+sig+"k>c o_k."+dot+"o_.c"+dot+metric.__name__+"(k,c)" 
        pre2 = " = 1 - %i%s"  % ((n-1), dot)
        
        c0 = "%1.2f" % num
        c1 = "%1.2f" % denom
        ml = max(len(c0), len(c1))
        c0 =  " " * ((ml - len(c0))/2) + c0
        c0 =  " " * ((ml - len(c1))/2) + c0
        calc  = " "*len(pre) + prec0          + " "*len(pre2) + c0          + "\n"
        calc += pre          + "-"*len(prec0) + pre2          + "-"*ml + " = %1.4f\n" % alpha
        calc +=  " "*len(pre) + prec1          + " "*len(pre2) + c1          + "\n"

        return alpha, calc

if __name__ == '__main__':

    print "Example alpha's from http://www.asc.upenn.edu/usr/krippendorff/webreliability2.pdf"
    print "(A) binary data, two observers, no missing"
    
    a = Reliability()
    meg  = "0 1 0 0 0 0 0 0 1 0".split()
    owen = "1 1 1 0 0 1 0 0 0 0".split()

    units = ["u-%s"%i for i in range(len(meg))]

    # test new API, silly input order
    for unit, value in zip(units, meg):
        a.addEntry(unit, 'meg', value)

    for unit, value in zip(units, owen):
        a.addEntry(unit, 'owen', value)

    alpha, calc = a.alpha(returncalc=True)

    print "Coincidence table:\n"
    print a.coinTable().toText()
    print "Data:\n"
    print a.getData().toText()
    print "\n"+calc
    print "\nAlpha: %1.3f" % (alpha)
    

    print "\n(B) nominal data, two observers, no missing"

    a = Reliability()
    ben = "a a b b d c c c e d d a".split()
    gerry = "b a b b b c c c e d d d".split()

    for b,g in zip(ben, gerry):
        a.addRow(b,g)
    alpha, calc = a.alpha(returncalc=True)

    print "Coincidence table:\n"
    print a.coinTable().toText()
    print "\n"+calc
    print "\nAlpha: %1.3f" % (alpha)
        
    print "\n(C) nominal data, k observers, missing values"

    a = Reliability()

    ob = [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None]
    oc = [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, None]
    od = [None, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, 3]
    oe = [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, None]

    for b,c,d,e in zip(ob, oc, od, oe):
        a.addRow(b,c,d,e)


    print "Coincidence table:\n"
    print a.coinTable().toText()

    alpha, calc = a.alpha(returncalc=True)
    print "\n"+calc
    print "\nNominal alpha: %1.3f" % (alpha)

    alpha, calc = a.alpha(returncalc=True, metric=m_interval)
    print "\n"+calc
    print "\nInterval alpha: %1.3f" % (alpha)

    alpha, calc = a.alpha(returncalc=True, metric=m_ratio)
    print "\n"+calc
    print "\nRatio alpha: %1.3f" % (alpha)

