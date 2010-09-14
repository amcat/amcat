import ont, dbtoolkit, toolkit
import cachable
import collections, re
db = dbtoolkit.amcatDB()                            

STOPLIST = set("van der den Veen MA Van de".split()) | set([""])

# niet in db:
# fassed, bikker, verhoeven, kooiman, lucas-smeerdijk, sharpe, elissen

adhoctk = {u'ko\u015fer kaya' : 1076,
         u'van der burg' : 903,
         u'van velzen' : 2619,
         u'aasted-madsen-van stiphout' : 995,
         u'aasted madsen-van stiphout' : 995,
         u'van vroonhoven-kok' : 913,
         u'plasterk' : 2769,
         u'dijksma' : 1249,
         u'eski' : 1375,
         u'van der veen' : 635,
         u'kraneveldt-van der veen' : 1235,
         u'bluemink' : 2588,
           u'algra' : 2337,
         }

adhocall = {
         u'ter horst' : 1912,
         u'cramer' : 2108,
         u'van bijsterveldt-vliegenthart' : 2742,
         u'de jager' : 1100,
         u'van middelkoop' : 799,
         u'van der laan' : 10820,
         u'bos' : 889,
         u'de vries' : 1144,
         u'middelkoop' : 799,
         }

adhocall.update(adhoctk)



def getWords(name):
    words = toolkit.stripAccents(name).lower().replace("-"," ").replace(","," ").split(" ")
    return set(words) - STOPLIST


class Politici(object):
    def __init__(self, objects, adhoc=None):
        self.objects = objects
        cachable.cache(self.objects, "name", "functions")
        self.words2objects = collections.defaultdict(set)
        for o in self.objects:
            for w in getWords(o.name):
                self.words2objects[w].add(o)
        self.adhoc = adhoc
    def getCandidates(self, name):
        cands = set()
        for w in getWords(name):
            cands |= self.words2objects[w]
        return cands

    def getPoliticus(self, name):
        name = name.replace("c.s.","").replace("\n"," ").strip().lower()
        if self.adhoc and name in self.adhoc: return ont.Object(db, self.adhoc[name])
        cands = self.getCandidates(name)
        if not cands:
            raise Exception("Cannot find %r" % name)
        if len(cands) == 1: return cands.pop()
        cands2 = set()
        w = getWords(name)
        for cand in cands:
            if getWords(cand.firstname) & w:
                cands2.add(cand)
        if not cands2:
            raise Exception("No suitable match for %r found in candidates %s" % (name, map(getNaamPartij, cands)))
        if len(cands2) > 1:
            raise Exception("Too many suitable matches for %r found in candidates %s: %s",
                            name, map(getNaamPartij, cands), map(getNaamPartij, cands2))
        return cands2.pop()

def getNaamPartij(o, date=None):
    result = "%s, %s%s" % (o.name, o.firstname, " "+o.prefix if o.prefix else "")
    for f in o.currentFunctions(date):
        if f.functionid == 0:
            result += " (%s)" % f.office.label
    return result

def getNaamPartijTuple(o, date=None):
    result = (o.name, o.firstname, o.prefix)
    for f in o.currentFunctions(date):
        if f.functionid == 0:
            return result + (f.office.label,)
    return result + (None,)

        

def getPolitici(db, fromdate=None, todate=None, onlytk=True):
    sql = "select p.objectid from o_politicians p inner join o_politicians_functions f on f.objectid = p.objectid"
    if onlytk: sql += " where office_objectid = 1608"
    for (name, op, date) in (('todate', ">=", fromdate), ('fromdate', "<=", todate)):
        if date:
            if type(date) not in (str,unicode): date = date.strftime("%Y-%m-%d")
            sql += " and ((%s is null) or (%s %s '%s') )" % (name, name, op, date)
    objs = [ont.Object(db, oid) for (oid,) in db.doQuery(sql)]
    adhoc = adhoctk if onlytk else adhocall
    return Politici(objs, adhoc)

if __name__ == '__main__':
    import datetime, sys
    p = getPolitici(db, datetime.date(2009, 9, 1), datetime.date(2010, 9, 1))
    #print getNaamPartij(p.getPoliticus("jan-jacob van dijk"))
    print getNaamPartij(p.getPoliticus((sys.argv + ["hamming"])[1]))
    
        
