import ont, dbtoolkit, toolkit
import cachable
import collections
db = dbtoolkit.amcatDB()                            

STOPLIST = set("van der den Veen MA Van de".split())

def getWords(name):
    words = name.lower().replace("-"," ").split(" ")
    return set(words) - STOPLIST


class Politici(object):
    def __init__(self, objects):
        self.objects = objects
        cachable.cache(self.objects, "name", "functions")
        self.words2objects = collections.defaultdict(set)
        for o in self.objects:
            for w in getWords(o.name):
                self.words2objects[w].add(o)
    def getCandidates(self, name):
        cands = set()
        for w in getWords(name):
            cands |= self.words2objects[w]
        return cands

    def getPoliticus(self, name):
        cands = self.getCandidates(name)
        if not cands:
            print ("Cannot find %r" % name)
            cands=name
            return cands
        if len(cands) == 1: return cands.pop()
        cands2 = set()
        w = getWords(name)
        for cand in cands:
            if getWords(cand.firstname) & w:
                cands2.add(cand)
        if not cands2:
            print("No suitable match for %r found in candidates %s" % (name, map(getNaamPartij, cands)))
            cands=name
            return cands
        if len(cands2) > 1:
            print("Too many suitable matches for %r found in candidates %s: %s",
                                            name, map(getNaamPartij, cands), map(getNaamPartij, cands2))
            cands=name
            return cands
        return cands2.pop()

def getNaamPartij(o, date=None):
    result = "%s, %s%s" % (o.name, o.firstname, " "+o.prefix if o.prefix else "")
    for f in o.currentFunctions(date):
        if f.functionid == 0:
            result += " (%s)" % f.office.label
    return result

        
        

def getPolitici(db, fromdate=None, todate=None):
    sql = "select p.objectid from o_politicians p inner join o_politicians_functions f on f.objectid = p.objectid"# where office_objectid = 1608"
    for (name, op, date) in (('todate', ">=", fromdate), ('fromdate', "<=", todate)):
        if date:
            if type(date) not in (str,unicode): date = date.strftime("%Y-%m-%d")
            sql += " and ((%s is null) or (%s %s '%s') )" % (name, name, op, date)
    objs = [ont.Object(db, oid) for (oid,) in db.doQuery(sql)]
    return Politici(objs)

if __name__ == '__main__':
    import datetime, sys
    p = getPolitici(db, datetime.date(2009, 9, 1), datetime.date(2010, 9, 1))
    #print getNaamPartij(p.getPoliticus("jan-jacob van dijk"))
    print getNaamPartij(p.getPoliticus((sys.argv + ["hamming"])[1]))
    
        
