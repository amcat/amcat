import toolkit

STOPLIST = "/home/amcat/resources/files/stoplist_dutch_2.txt"

F_THRES = 5
C_THRES = 6.63 # assuming 1df

def chi2(a,b,c,d):
    def ooe(o, e):
        #print "ooe(%s,%s)=%s" % (o,e,(o-e)*(o-e) / e)
        return (o-e)*(o-e) / e
    chi2 = 0
    tot = 0.0 + a+b+c+d
    #print a,b,c,d
    chi2 += ooe(a, (a+c)*(a+b)/tot)
    chi2 += ooe(b, (b+d)*(a+b)/tot)
    #print "%s * %s / %s = %s" % (a+c, c+d, tot, ((a+c)*(c+d)/tot))
    chi2 += ooe(c, (a+c)*(c+d)/tot)
    chi2 += ooe(d, (d+b)*(c+d)/tot)
    return chi2

class Chi2:
    def __init__(self, db):
        self.db = db
        self.wc = toolkit.DefaultDict(lambda: toolkit.DefaultDict(int))
        self.ac = toolkit.DefaultDict(int)
        self.nn = toolkit.DefaultDict(int)
        self.cids = set()
        self.stoplist = set(x.strip() for x in open(STOPLIST).readlines())

    def add(self, cid, aid):
        art = self.db.article(aid)
        self.cids.add(cid)
        n = 0
        for word in art.words(onlyWords=True):
            word = word.lower()
            if word not in self.stoplist:
                self.wc[cid][word] += 1
                n += 1
        self.ac[cid] += 1
        self.nn[cid] += n
                
    def words(self, cid):
        for word in self.wc[cid]:
             f1 = self.wc[cid][word]
             if f1 < F_THRES: continue
             n1 = self.nn[cid]

             f2, n2 = 0, 0
             for cid2 in self.cids:
                 if cid2 == cid: continue
                 f2 += self.wc[cid2][word]
                 n2 += self.nn[cid2]
             chi = chi2(f1, f2, n1-f1, n2-f2)
             expf = float(f2) * n1 / n2
             if expf > f1: continue
             if chi >= C_THRES:
                 yield (word, chi, n1, f1, expf)

    def allwords(self):
        for cid in self.cids:
            for data in self.words(cid):
                yield tuple([cid] + list(data))
                
if __name__ == '__main__':
    import dbtoolkit
    c = Chi2(dbtoolkit.anokoDB())
    c.add("verdonk7",   33372267 )
    c.add("verdonk7",   33372264 )
    c.add("verdonk7",   33372385 )
    c.add("balkje7",    33368172 )
    c.add("balkje7",    33368248 )
    c.add("balkje7",    33668099 )

    for data in c.allwords():
        print toolkit.join(data)
    
