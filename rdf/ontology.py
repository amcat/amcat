import pySesameDB, re,toolkit,pickle,labels
from categories import *

OMKLAPREL = 'http://www.content-analysis.org/vocabulary/net#Omklap'
OMKLAPROOTS = ['http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-6-richtingen', 'http://www.content-analysis.org/vocabulary/ontologies/zurich#zurichcat']
NUMMERREL = 'http://www.content-analysis.org/vocabulary/net#Nummer'
ZUNUMREL = 'http://www.content-analysis.org/vocabulary/ontologies/zurich#number'
ZUCATREL = 'http://www.content-analysis.org/vocabulary/ontologies/zurich#catstr'

CACHE = '/home/anoko/tmp/ontology.pickle'

SERQL = """
SELECT X,Y,Z FROM
       {X} net:InOntology {k06:k06test}; Y {Z}
"""


def tostring(x):
    if x is None: return x
    if x == "http://www.openrdf.org/schema/serql#directSubClassOf": return "sub"
    if x == "http://www.openrdf.org/schema/serql#directSuperClassOf": return "super"
    m = re.match("http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-\d+-(.*)", x)
    if m:
        return m.group(1)
    return x

class Ontology:

    def __init__(self, db):
        self.ids = {} # name : id
        self.names = [] # id : name

        self.relids = {}
        self.relnames = []

        self.cats = {} # system : {object : cat, ..} 
        
        self.ont = {}
        self.db = db
        self._initOntology()
        
    def lookuprel(self, name):
        if name not in self.relids:
            #print "Unknown %s, creating new rel" % name
            i = len(self.relnames)
            self.relids[name] = i
            self.relnames.append(name)
            return i
        return self.relids[name]        

    def rlookuprel(self, relid):
        return self.relnames[relid]

    def rlookup(self, id):
        return self.names[id]

    def lookup(self, name):
        if name not in self.ids:
            print "Unknown name: %s" % name
            i = len(self.names)
            self.ids[name] = i
            self.names.append(name)
            return i
        return self.ids[name]

    def _initOntology(self):
        try:
            f = open(CACHE)
            self.relids, self.relnames, self.names, self.ids, self.ont = pickle.load(f)
        except Exception, e:
            toolkit.warn(e)
            ont = self.ont
            
            for obj, rel, other in self.db.execute(SERQL):
                r = self.lookuprel(rel)
                i = self.lookup(obj)
                j = self.lookup(other)

                if i not in ont: ont[i] = {}
                if r not in ont[i]: ont[i][r] = []
                ont[i][r].append(j)


            pickle.dump((self.relids, self.relnames, self.names, self.ids, self.ont), open(CACHE, 'w'))
            
    def categorize(self, object, system = CAT_ISSUE_FIRST):
        rels = set([self.lookuprel(self.db.nsexpand(x)) for x in system[0]])
        if system not in self.cats:
            self.cats[system] = {}
        cat = self.cats[system]
        roots = [self.lookup(self.db.nsexpand(x)) for x in system[1]]
        cats = {}
        for root in system[1]:
            r = self.lookup(self.db.nsexpand(root))
            for c in categories[root]:
                c = self.lookup(self.db.nsexpand(c))
                cats[c] = (r, c, 1)
        #print "Categorizing %r" % object
        object = self.lookup(object)
        rc = self._cat(object, rels, cat, roots, cats)
        if rc is None:
            return None, None, None
        else:
            return self.rlookup(rc[0]), self.rlookup(rc[1]), rc[2]

    def _str(self, o):
        return db.nscollapse(self.rlookup(o))
    def _strel(self, o):
        return db.nscollapse(self.rlookuprel(o))

    def _cat(self, o, rels, cat, roots, cats):
        if o in cat:
            return cat[o]
        if o in cats:
            return cats[o]

        omklap = self.ont.get(o, {}).get(self.lookuprel(OMKLAPREL), None)
        if omklap: omklap = self.rlookup(omklap[0])
        else: omklap = 1
        
        res = None
        index = None
        #print rels
        #print " Looking up %r : %r" % (self.rlookup(o), self.ont.get(o, None))
        #for k,v in self.ont.get(o, {}).items():
        #    print ' + (%s) %s' % (k, self.db.nscollapse(self.rlookuprel(k)))
        #    for z in v:
        #        print '   .', self.db.nscollapse(self.rlookup(z))
        for rel in rels:
            for p in self.ont.get(o,{}).get(rel, []):
                #print "  considering %s -> %s" % (self._strel(rel), self._str(p))
                rc = self._cat(p, rels, cat, roots, cats)
                if rc:
                    #print "  ... candidate: %s" % (self.rlookup(rc[1]))
                    ic = list(roots).index(rc[0])
                    if index is None or ic < index:
                        index = ic
                        res = rc

        #print "  ... best candidate: %s" % `res`
        if res:
            res = list(res)
            if res[0] in [self.lookup(omklaproot) for omklaproot in  OMKLAPROOTS]:
                res[2] = res[2] * omklap
            else:
                res[2] = None
            res = tuple(res)
            cat[o] = res
        return res

    def zurichcat(self, o, omklap  = 1):
        SCREL = self.lookuprel(self.db.nsexpand("rdfs:subClassOf"))
        CATREL = self.lookuprel(self.db.nsexpand("zu:incategory"))
        rels = self.ont.get(o)


        result = [None, None, None, None]

        if rels is None:
            return result
        cat = rels.get(CATREL, None)
        if cat:
            cat = cat[0]
            result = []
            while cat:
                result.insert(0, self.rlookup(cat))
                cat = self.ont.get(cat).get(SCREL, [None])[0]
            result = result[1:] # chop root
            result = result + [None] * (3 - len(result)) + [omklap]
        else:
            #print "%s has no zurichcat, trying parents"
            om = self.ont.get(o, {}).get(self.lookuprel(OMKLAPREL), None)
            if om: omklap *= self.rlookup(om[0])
                    
            for parent in rels.get(SCREL, []):
                #print "trying %s : %s" % (parent, self._str(parent))
                result = self.zurichcat(parent, omklap)
        return result
            
            
    def concept(self, url):
        return Concept(url, self.db, self.ont.get(self.lookup(url), {}))

class Concept:
    def __init__(self, url, db, rels):
        self.url = url
        self.db = db
        self.rels = rels
        self.ont = db and db.ontology() or None

    def shorturl(self):
        return self.db.nscollapse(self.url)

    def __eq__(self, other):
        return type(self) == type(other) and self.url == other.url

    def label(self):
        return self.db.label(self.url)
    __str__ = label

    def nummer(self):
        nr = self.rels.get(self.ont.lookuprel(NUMMERREL), None)
        if nr:
            return self.ont.rlookup(nr[0])
        else:
            return None

    def zunummer(self):
        nr = self.rels.get(self.ont.lookuprel(ZUNUMREL), None)
        if nr:
            return self.ont.rlookup(nr[0])
        else:
            return None

    def zucat(self):
        nr = self.rels.get(self.ont.lookuprel(ZUCATREL), None)
        if nr:
            s = self.ont.rlookup(nr[0])
            ss = s.split(".")
            if len(ss) > 2:
                s = "%s.%s" % ("".join(ss[:-1]), ss[-1])
            else:
                s = "".join(ss)
            return float(s)
                           
        else:
            return None
        
    
    def cat(self, system, labels = True, concepts = False):
        rco = self.ont.categorize(self.url, system=system)
        if concepts and rco:
            return self.ont.concept(rco[0]), self.ont.concept(rco[1]), rco[2]
        elif labels and rco:
            return self.db.label(rco[0]), self.db.label(rco[1]), rco[2]
        else:
            return rco        

    def cat_af(self, labels = True, concepts = False):
        return self.cat(system = CAT_ACTOR_FIRST, labels=labels, concepts = concepts)
    
    def cat_if(self, labels = True, concepts = False):
        return self.cat(system = CAT_ISSUE_FIRST, labels=labels, concepts = concepts)

    def cat_th(self, labels=  True, concepts = False):
        #result = self.cat(system = CAT_THEMA_FIRST, labels=labels, concepts = concepts)
        #print self, '--->', result
        #try:
        #    print result[0], result[0].nummer(), result[1], result[1].nummer()
        #except Exception, e:
        #    print e
        return self.cat(system = CAT_THEMA_FIRST, labels=labels, concepts = concepts)

    def cat_thaf(self, labels=True, concepts = False):
        #print self, '--->', self.cat(system = CAT_TH_ACTOR_FIRST, labels=labels, concepts = concepts)
        return self.cat(system = CAT_TH_ACTOR_FIRST, labels=labels, concepts = concepts)

    def cat_zurich(self, labels = True, concepts = False):
        rco = self.ont.zurichcat(self.ont.lookup(self.url))
        if concepts and rco:
            return rco[0] and self.ont.concept(rco[0]), rco[1] and self.ont.concept(rco[1]), rco[2] and self.ont.concept(rco[2]), rco[3]
        elif labels and rco:
            return rco[0] and self.db.label(rco[0]), rco[1] and self.db.label(rco[1]), rco[2] and self.db.label(rco[2]), rco[3]
        else:
            return rco
                                            

    def __repr__(self):
        return "<@%s>" % self.db.nscollapse(self.url)

concepttype = type(Concept(None, None, None))



def strng(uri):
    if not uri: return uri
    return uri.split('-')[-1]

if __name__ == '__main__':
    import rdftoolkit
    db = rdftoolkit.anokoRDF()
    o = Ontology(db)

    #for k,v in o.ont.items():
    #    print o.db.nscollapse(o.rlookup(k))
    #    for rel, others in v.items():
    #        print " +", o.db.nscollapse(o.rlookuprel(rel))
    #        for other in others:
    #            print "   . ", o.db.nscollapse(o.rlookup(other))

    #for name, system in ('Richting,Actor',CAT_ISSUE_FIRST), ('Actor,Richting', CAT_ACTOR_FIRST), ('Thema,Actor', CAT_THEMA_FIRST):

    objs = ['http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-60257-minimumloon'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-6024-socialemarkteconomiearbeidsmarkteconomie'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-60253-bijstand'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-60231-verzorgingsstaat'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-60238-strengerekeuringen'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-60233-armoede'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-505272-usmedia'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-61056-uitzettingimmigranten'  
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-610575-protesttegenuitzetting'
            ,'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-6163-gezondheidszorg'
            ]

    for obj in objs:
        #obj = o.lookup(obj)
        #print "Lookup up obj: %s" % obj
        con = o.concept(obj)
        cat = con.cat_zurich(False, True)
        print con
        print cat
        print "-->",[(c.zunummer(),c.zucat()) for c in cat[:-1] if c], cat[-1]


