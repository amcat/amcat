from cachable import Cachable, DBPropertyFactory
import collections, toolkit, enum, categorise
try:
    import mx.DateTime as my_datetime
except:
    from datetime import datetime as my_datetime
from idlabel import Identity, IDLabel

class Base(IDLabel):
    def __init__(self, ont, id, label=None):
        IDLabel.__init__(self, id, label)
        self.ont = ont
    def __str__(self):
        return self.getLabel()
    def getLabel(self):
        return self.label

class Function(object):
    def __init__(self, person, function, office, fromdate=None, todate=None, cand=False):
        self.person = person
        self.function = function
        self.office = office
        self.fromdate = fromdate
        self.todate = todate
        self.cand = cand
    def __str__(self):
        return "Function('%s', %s, '%s', %s - %s)" % (self.person.getLabel(), self.function.label, self.office.getLabel(),
                                                 self.fromdate and toolkit.writeDate(self.fromdate), self.todate and toolkit.writeDate(self.todate))

class Functions(object):
    def __init__(self, ont):
        self.ont = ont
        self.db = ont.db
        self.functionenum = functionEnumFromDB(self.db)
        self.byperson = collections.defaultdict(list) # {person : set(function)}
        self.byoffice = collections.defaultdict(list) # {office : set(function)}
        self.initfunctions()
    def initfunctions(self):
        for oid, func, office, fromdate, todate, cand in self.db.doQuery(
            "select objectid, functionid, office_objectid, fromdate, todate, candidate from o_politicians_functions"):
            oid = self.ont.objects[oid]
            office = self.ont.objects[office]
            func = self.functionenum.fromValue(func)
            if fromdate.year == 1753: fromdate = None
            f = Function(oid, func, office, fromdate, todate, cand)
            self.byperson[oid].append(f)
            self.byoffice[office].append(f)
    def getChildren(self, office, date=None):
        if date is None: date = my_datetime.now()
        return selectFunctionsByDate(date, self.byoffice[office])
    def getParents(self, person, date=None):
        if date is None: date = my_datetime.now()
        return selectFunctionsByDate(date, self.byperson[person])

def selectFunctionsByDate(date, functions):
    for f in functions:
        if ((f.fromdate is None or f.fromdate < date)
            and (f.todate is None or f.todate > date)):
            yield f
def functionEnumFromDB(db):
        e = enum.Enum()
        for fid, lbl, desc in db.doQuery("select functionid, label, description from o_functions"):
            e.add(enum.EnumValue(lbl, value=fid))
        return e


class Object(Base, Cachable):
    __table__ = 'o_objects'
    __idcolumn__ = 'objectid'
    keyword = DBPropertyFactory(table="o_keywords")
    lastname = DBPropertyFactory(fieldname="name", table="o_politicians")
    firstname = DBPropertyFactory(table="o_politicians")
    prefix = DBPropertyFactory(table="o_politicians")
    nr = DBPropertyFactory()
    
    def __init__(self, ont, id, **cache):
        Cachable.__init__(self, ont.db, id, **cache)
        Base.__init__(self, ont, id)
        self.parents = {} # clas : (parent or None, omklap?)
        self.children = collections.defaultdict(set) # clas : [parenr, reverse]
        self.labels = {} # language : label
        self.label = None
    def getNr(self):
        return self.nr
    def setNr(self, nr):
        old = self.nr
        self.nr = nr
        self.ont.setNodeNr(self, nr, old)
    def setParent(self, clas, parent, omklap=1):
        #if self.id == 2583: print clas, parent, omklap
        if type(parent) == Class: parent = self.parents[parent][0]
        self.parents[clas] = (parent, omklap)
        if parent: parent.children[clas].add((self, omklap))
        clas.addObject(self)
    def getChildren(self, clas, includeFunctions=False, functionsDate=None):
        if type(clas) == int:
            clas = self.ont.classes[clas]
        for o, r in self.children[clas]:
            yield o
        if includeFunctions:
            for f in self.ont.functions.getChildren(self, functionsDate):
                yield f.person
    def getParents(self, clas, date=None, includeReverse = False):
        if clas in self.parents:
            (p,r) = self.parents[clas]
            if p is None:
                yield (clas, 1) if includeReverse else clas
            else:
                yield (p,r) if includeReverse else p
        for f in self.ont.functions.getParents(self, date):
            yield (f.office, 1) if includeReverse else f.office
        
    def getParent(self, clas):
        if type(clas) == int:
            clas = self.ont.classes[clas]
        return self.parents.get(clas, (None, None))[0]
    def getLabel(self, lang=None):
        if not self.labels: return None
        l = self.labels
        if lang and lang in l: return l[lang]
        if 2 in l: return l[2]
        keys = l.keys()
        keys.sort()
        return l[keys[0]]
    def setLabel(self, lang, label):
        self.labels[lang] = label
        if self.label is None: self.label = label
        
    def getParties(self, date=None):
        SQL = "select party_objectid, fromdate, todate from o_politicians_parties where objectid=%i" % self.id
        if date: SQL += " and fromdate < %s and (todate is null or todate > %s)" % (toolkit.quotesql(date), toolkit.quotesql(date))
        for p, fro, to in self.db.doQuery(SQL):
            yield (self.ont.objects[p], fro, to)
    def getFunctions(self, date=None):
        SQL = "select functionid, office_objectid, fromdate, todate from o_politicians_functions where objectid=%i" % self.id
        if date: SQL += "and fromdate < %s and (todate is null or todate > %s)""" % (toolkit.quotesql(date), toolkit.quotesql(date))
        for f, p, fro, to in self.db.doQuery(SQL):
            yield f, self.ont.objects[p], fro, to
    def getSearchString(self, date=None, xapian=False):
        if not date: date = my_datetime.now()
        if self.keyword: return self.keyword.replace("\n"," ")
        if self.lastname:
            ln = self.lastname
            if "-" in ln or " " in ln:
                ln = '"%s"' % ln.replace("-", " ")
            conds = []
            if self.firstname:
                conds.append(self.firstname)
            for p, fro, to in self.getParties(date):
                k = p.getSearchString()
                if not k: k = '"%s"' % p.getLabel().replace("-"," ")
                conds.append(k)
            for f, p, fro, to in self.getFunctions(date):
                k = p.getSearchString()
                if not k: k = '"%s"' % p.getLabel().replace("-"," ")
                conds.append(k)
                conds += function2conds(f, p)
            if conds:
                if xapian:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s" % x.strip() for x in conds),)
                else:
                    kw = "%s AND (%s)" % (ln, " OR ".join("%s^0" % x.strip() for x in conds),)
            else:
                kw = ln
            return kw.replace("\n"," ")
    def categorise(self, cat, *args, **kargs):
        if type(cat) == int: cat = self.ont.categorisations[cat]
        return cat.categorise(self, *args, **kargs)
    categorize=categorise
    def generateNr(self):
        if self.nr: return self.nr
        if not self.parents:
            toolkit.warn("Node has no parents??? %s" % self.getLabel())
            return False
        parents = set()
        for c, (p,o) in self.parents.items():
            nr = p.getNr() if p else Number(c.id)
            hasp = True
            if nr: 
                parents.add(nr)
        if not parents:
            toolkit.warn("All parent nodes have no number?? %s" % self.getLabel())
            return False
        lowest = sorted(parents)[0]
        nr = nextnr(lowest, set(self.ont.bynr.keys()))
        print "%s\t%s\t%s" % (self.label, ",".join(str(x) for x in parents), nr)
        self.setNr(nr)
        return nr
    
def function2conds(func, office):
    if office.id in (380, 707, 729, 1146, 1536, 1924, 2054, 2405, 2411, 2554, 2643):
        if func == 2:
            return ["bewinds*", "minister*"]
        else:
            return ["bewinds*", "staatssecret*"]
    if office.id == 901:
        return ["premier", '"minister president"']
    if office.id == 548:
        return ["senator", '"eerste kamer*"']
    if office.id == 1608:
        return ["parlement*", '"tweede kamer*"']
    if office.id == 2087:
        return ['"europ* parlement*"', "europarle*"]
    return []

class Class(Base):
    def __init__(self, ont, id, label):
        Base.__init__(self, ont, id, label)
        self.objects = set()
    def getRoots(self):
        for o in self.objects:
            if not o.getParent(self):
                yield o
    def addObject(self, obj):
        self.objects.add(obj)
        
class Set(Base):
    def __init__(self, ont, id, label):
        Base.__init__(self, ont, id, label)
        self.objects = set()

class Ontology(Cachable):
    def __init__(self, db):
        Cachable.__init__(self, db, -1)
        self.objects = {} # oid : object
        self.classes = {} # classid : class
        self.sets = {} # setid : set
        self.bynr = {} # nr : object
        self.nodes = self.objects
        self.addFunctionProperty("functions", lambda : Functions(self))
        self.addFunctionProperty("categorisations", self.getCategorisations)
    def setNodeNr(self, node, newnr, oldnr=None):
        if oldnr and oldnr in self.bynr:
            del self.bynr[oldnr]
        if newnr in self.bynr:
            raise Exception()
        self.bynr[newnr] = node
    def createObject(self, oid, nr):
        if oid in self.objects: raise Exception()
        o = Object(self, oid, nr=nr)
        self.objects[oid] = o
        if nr:
            self.setNodeNr(o, nr)
        return o
    def createClass(self, cid, lbl):
        if cid in self.classes: raise Exception()
        c = Class(self, cid, lbl)
        self.classes[cid] = c
        return c
    def createSet(self, setid, name):
        if setid in self.sets: raise Exception()
        s = Set(self, setid, name)
        self.sets[setid] = s
        return s
    def getCategorisations(self):
        return dict((cid, categorise.Categorisation(self, cid)) for (cid,) in
                    self.db.doQuery("select categorisationid from o_categorisations"))
    def getCategorisation(self, catid):
        return self.categorisations[catid]
    
_ontology = None
def getOntology(db):
    global _ontology
    if _ontology is None:
        _ontology = fromDB(db)
    return _ontology
        
def fromDB(db):
    o = Ontology(db)
    for oid, nr in db.doQuery("SELECT objectid, cast(nr as varchar(255)) FROM o_objects"):
        if nr: nr = Number(nr)
        try: o.createObject(oid, nr)
        except: print 'Object %s could not be created!' % oid
    for oid, lang, lbl in db.doQuery("SELECT objectid, languageid, label FROM o_labels"):
        o.objects[oid].setLabel(lang, lbl)
    for cid, lbl in db.doQuery("SELECT classid, label FROM o_classes"):
        o.createClass(cid, lbl)
    for cid, childid, parentid, linkid, reverse in db.doQuery("SELECT classid, childid, parentid, link_classid, reverse FROM o_hierarchy"):
        clas = o.classes[cid]
        child = o.objects[childid]
        if parentid: parent = o.objects[parentid]
        elif linkid: parent = o.classes[linkid]
        else: parent = None
        reverse = -1 if reverse else 1
        child.setParent(clas, parent, reverse)
    for setid, name in db.doQuery("SELECT setid, name FROM o_sets"):
        o.createSet(setid, name)
    for setid, oid in db.doQuery("SELECT setid, objectid FROM o_sets_objects"):
        o.sets[setid].objects.add(o.objects[oid])
    return o
        
NUMBER_SECOND_PERIOD = "."
class Number(Identity):
    def __init__(self, string_or_clas, major=0, minor=0):
        if type(string_or_clas) in (str, unicode):
            self.major, self.minor, self.clas = 0,0,0
            comps = string_or_clas.split(".")

            self.clas = int(comps[0])
            if len(comps) == 2:
                mami = comps[1]
                if len(mami) > 3:
                    self.major = int(mami[:3])
                    self.minor = int(mami[3:10])
                else:
                    self.major = int(mami)
            elif len(comps) == 3:
                self.major, self.minor = int(comps[1]), int(comps[2])
        else:
            self.clas, self.major, self.minor = int(string_or_clas), int(major), int(minor) 

    def __add__(self, other):
        return Number(self.clas + other.clas, self.major + other.major, self.minor + other.minor)
    def __str__(self):
        return "%s.%03i%s%07i" % (self.clas, self.major, NUMBER_SECOND_PERIOD, self.minor)
    def identity(self):
        return (self.__class__, self.clas, self.major, self.minor)
    def toSQLString(self):
        return "%s.%03i%07i" % (self.clas, self.major, self.minor)

def catlabel(x):
    if x is None: return None
    if type(x) == Object: return x.getLabel(2)
    return x.label
        
def recurse(obj, cl, depth, parent=None, cat=None, done=set()):
    if cat and cat.set and obj not in cat.set.objects: return
    if obj in done: return
    done.add(obj)
    fields = [obj.id, obj.nr]
    if cat:
        c = cat.getCategorisation(obj)
        fields += map(catlabel, c)
    fields += ["%s%s" % ("    "*depth, obj.getLabel(2))]
    fields += [obj.lastname, obj.firstname]
    l = list(obj.getParties())
    if l:
        if len(l) > 1:
            l2 = [x for x in l if x[0] == parent]
            if l2: l = l
            l.sort(key = lambda x : x[1], reverse=True)
        party, fr,to = l[0]
        if fr.year == 1753: fr = None
        fr = toolkit.writeDate(fr) if fr else "-"
        to = toolkit.writeDate(to) if to else "-"
        fields += [party.getLabel(2), fr, to]
    else:
        fields += ["","",""]
    l = list(obj.getFunctions())
    if l:
        if len(l) > 1:
            l2 = [x for x in l if x[1] == parent]
            if l2: l = l
            l.sort(key = lambda x : x[2], reverse=True)
        func, off, fr, to = l[0]
        if fr.year == 1753: fr = None
        fr = toolkit.writeDate(fr) if fr else "-"
        to = toolkit.writeDate(to) if to else "-"
        func = ["lid", "leider", "vice-leider", "staatshoofd"][func-1]
        fields += [off.getLabel(2), func, fr, to]
    else:
        fields += ["","","", ""]
    fields += [obj.keyword, obj.getSearchString()]
    print toolkit.join(fields)
    children = obj.getChildren(cl, includeFunctions=cat.functions)
    if cat:
        children = cat.sort(children)
    for c in children:
        recurse(c, cl, depth+1, parent=obj, cat=cat, done=done)

def printSet(ont, setid, cat):
    #cat = ont.getCategorisation(catid, setid)
    print toolkit.join(["id", "nr", "class","root","cat","subcat","subcat2", "label","name","firstname","party (most recent)","(from)","(to)", "office (recent)", "function", "(from)", "(to)","keywords (defined)", "keywords"])
    for c in cat.classes:
        for o in cat.sort(c.getRoots()):
            recurse(o, c, 1, cat=cat)
            

# number business

_NR_EXP1 = 3 # 1000
_NR_EXP2 = 3 # .001
_NR_EXP3 = 7 # .0010000001

_NR_INC1 = Number("1%s" % ("0"*_NR_EXP1)) # 4000
_NR_INC2 = Number("0.%s1" % ("0"*(_NR_EXP2 - 1))) # 0.001
_NR_INC3 = Number("0.%s1" % ("0"*(_NR_EXP2 + _NR_EXP3 - 1))) # 0.0000000001

def nextnr(nr, inuse):
    if nr.major: inc = Number(0,0,1)
    else: inc = Number(0,1,0)
    while nr in inuse: nr += inc
    return nr


def createObject(db, classid, parentid, label, lang=2, sets=[]):
    oid = db.insert("o_objects", dict(nr=None))
    db.insert("o_hierarchy", dict(childid=oid, parentid=parentid, classid=classid), retrieveIdent=False)
    if type(label) == str: label = label.decode('ascii')
    label = label.encode('ascii')
    db.insert("o_labels", dict(objectid=oid, languageid=lang, label=label), retrieveIdent=False)
    for set in sets:
        db.insert("o_sets_objects", dict(objectid=oid, setid=set),  retrieveIdent=False)
    return oid

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.anokoDB()
    ont = fromDB(db)

    o = ont.nodes[15619]
    print o
    print o.label
    print o.nr
