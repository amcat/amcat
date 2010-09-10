import decimal, toolkit, sys


# Number business

_NR_EXP1 = 3 # 1000
_NR_EXP2 = 3 # .001
_NR_EXP3 = 7 # .0010000001

_NR_INC1 = decimal.Decimal("1%s" % ("0"*_NR_EXP1)) # 4000
_NR_INC2 = decimal.Decimal(".%s1" % ("0"*(_NR_EXP2 - 1))) # 0.001
_NR_INC3 = decimal.Decimal(".%s1" % ("0"*(_NR_EXP2 + _NR_EXP3 - 1))) # 0.0000000001

def nextnr(parent, inuse):
    nr = parent.getNr()
    i = _NR_INC3 
    if len(str(nr)) <= 4: i = _NR_INC2
    while nr in inuse: nr += i
    return nr
def str2nr(s):
    if not s: return None
    check = decimal.Decimal(s)
    i = s.index(".")
    s = s[:s.index(".")+11]
    if s[-7:] == '0000000':
        s = s[:-7]
        if s[-3:] == '000':
            s = s[:-3]
    nr = decimal.Decimal(s)
    if check <> nr: raise Exception("%s <> %s" % (check, nr)) # shouldn't happen
    return nr
def newnr(node):
    #debug = node.label == "ec94 Bangemann, Martin"
    if node.getNr(): return node.getNr()
    parents = set(); hasp=False
    for p in node.getParents(restricted=True):
        hasp = True
        if not p.getNr(): return False
        parents.add(p)
    if not hasp:
        toolkit.warn("Node has no parents??? %s" % node.label)
        return False
    def comp(x,y):
        x = x.getNr()
        y = y.getNr()
        xmaj = x == int(x)
        ymaj = y == int(y)
        if xmaj and not ymaj: return 1
        if ymaj and not xmaj: return -1
        return cmp(x, y)
    parents = sorted(parents, comp)
    #if debug: toolkit.warn(",".join("%s:%s" % (x.label, x.getNr()) for x in parents))
    lowest = parents[0]
    nr = nextnr(lowest, node.ont.nrs)
    print "%s\t%s\t%s" % (node.label, ",".join("%s:%s" % (x.label, x.getNr()) for x in parents), nr)
    #if debug: sys.exit(1)
    node.setNr(nr)
    return nr

class Node(object):
    def __init__(self, ont, oid, label, ontologid=None):
        self.ont = ont
        self.oid = oid
        self.label = label
        self.ontologyid = ontologid
        self._uri = None
        self._categories = {}
    def getLabel(self, language=None):
        if language:
            label = self.ont.db.getValue("select label from ont_labels where objectid=%i and language=%i" % (self.oid, language))
            if label:return label
        return self.label
    def getNr(self):
        if not '_nr' in dir(self):
            self.ont.loadNrs()
        return self._nr
    def getURI(self):
        if not self._uri:
            self.ont.loadURIs()
        return self._uri
    def hasAncestor(self, node):
        for p in self.getParents():
            if p == node: return True
            if p.hasAncestor(node): return True
        return False
    def getDescendants(self, paths=None, restricted=False):
        """paths can be None, 'path', or 'relations'"""
        for c in self.getChildren(restricted=restricted, relations=paths=='relations'):
            yield [c] if paths else c
            node = c[0] if paths=='relations' else c
            for d in node.getDescendants(paths=paths, restricted=restricted):
                yield [c] + d if paths else d
    def __cmp__(self, other):
        if not isinstance(other, Node): return -1
        return cmp(self.label.lower(), other.label.lower())
    def __str__(self):
        return "[%s %s:%s]" % (type(self).__name__, self.oid, self.label)
    def setNr(self, nr):
        if self._nr: raise Exception("Already has number")
        self._nr = nr
        self.ont.nrs[nr] = self
    def getCategories(self, catid):
        if catid not in self._categories:
            sql = """select root_objectid, cat_objectid, omklap, validfrom, validto
            from ont_objects_categorizations
            where categorizationid=%i and objectid=%i""" % (catid, self.oid)
            self._categories[catid] = [
                (self.ont.nodes[roid], self.ont.nodes[coid], 1 - omklap * 2, vfrom, vto)
                for (roid, coid, omklap, vfrom, vto)
                in self.ont.db.doQuery(sql)
                ]
        return self._categories[catid]

    def categorize(self, catid, date):
        for roid, coid, omklap, vfrom, vto in self.getCategories(catid):
            if (((vfrom is None) or (vfrom <= date)) and
                ((vto is None) or (vto > date))):
                return roid, coid, omklap
        return None, None, None
        
    def categorize_oud(self, catid, date):
        date = "'%s'" % toolkit.writeDate(date)
        sql = """select root_objectid, cat_objectid, omklap from ont_objects_categorizations
                 where categorizationid=%i and objectid=%i
                 AND (validfrom is null OR validfrom <= %s)
                 AND (validto is null OR validto > %s)
                 """ % (catid, self.oid, date, date)
        cats = self.ont.db.doQuery(sql)
        if len(cats) == 0: return None, None, None
        if len(cats) > 1: raise Exception("Ambiguous categorizaition!")
        roid, coid, omklap = cats[0]
        return self.ont.nodes[roid], self.ont.nodes[coid], 1 - omklap * 2 

        

class Relation(object):
    def __init__(self, subject, predicate, object):
        self.subject = subject
        self.predicate = predicate
        self.object = object

class Role(Node, Relation):
    def __init__(self, rsubj, pred, robj, datefrom, dateto, ont, oid, label):
        Node.__init__(self, ont, oid, label)
        Relation.__init__(self, rsubj, pred, robj)
        self.datefrom = datefrom
        self.dateto = dateto
        rsubj.outgoing.add(self)
        robj.incoming.add(self)

class Instance(Node):
    def __init__(self, *args, **kargs):
        Node.__init__(self, *args, **kargs)
        self.classes = set()
        self.outgoing = set()
        self.incoming = set()
        self.literal = {} # {predicate : value}
    def addRelation(self, predicate, object):
        assert not (predicate.literal or predicate.temporal)
        r = Relation(self, predicate, object)
        self.outgoing.add(r)
        object.incoming.add(r)
    def setLiteral(self, predicate, value):
        assert predicate.literal
        self.literal[predicate] = value
    def getParents(self, restricted=False):
        for c in self.classes:
            if not (restricted and self.relatedToInstanceOf(c)):
                yield c
        for rel in self.outgoing:
            yield rel.object
    def getChildren(self, restricted="dummy", relations=False):
        for rel in self.incoming:
            yield (rel.subject, rel) if relations else rel.subject 
    def relatedToInstanceOf(self, klass):
        for rel in self.outgoing:
            if klass in rel.object.classes: return True
            if rel.object.relatedToInstanceOf(klass): return True
        return False
        
class Class(Node):
    def __init__(self, *args, **kargs):
        Node.__init__(self, *args, **kargs)
        self.subclasses = set()
        self.superclasses = set()
        self.instances = set()
    def addInstance(self, i):
        self.instances.add(i)
        i.classes.add(self)
    def addSubclass(self, c):
        self.subclasses.add(c)
        c.superclasses.add(self)
    def getParents(self, restricted = "dummy"):
        for c in self.superclasses:
            yield c
    def getChildren(self, restricted=False, relations=False):
        for c in self.subclasses:
            yield (c, "subclass") if relations else c
        for i in self.instances:
            if not (restricted and i.relatedToInstanceOf(self)):
                yield (i, "instance") if relations else i
        
class Predicate(Node):
    def __init__(self, domain, range, temporal, *args, **kargs):
        Node.__init__(self, *args, **kargs)
        assert isinstance(domain, Class)
        assert (not range) or isinstance(range, Class)
        self.domain = domain
        self.range = range
        self.temporal = temporal
        self.literal = not range
        assert not (self.literal and self.temporal)

class Ontology(object):
    def __init__(self, db):
        self.nodes = {} # oid : node
        self.labels = {} # label : node
        self.uris = {}
        self.nrs = {}
        self.db = db
    def addNode(self, node):
        if node.label.lower() in self.labels:
            pass#print >>sys.stderr, "Duplicate label: %s" % node.label
        if node.oid in self.nodes: raise Exception("Duplicate oid: %s" % node.oid)
        self.nodes[node.oid] = node
        self.labels[node.label.lower()] = node
    def loadURIs(self):
        if self.uris: return
        SQL = "SELECT objectid, uri from ont_objects o"
        for oid, uri in self.db.doQuery(SQL):
            if not uri: continue
            if uri.lower() in self.uris: raise Exception("Duplicate uri: %s" % uri)
            self.nodes[oid]._uri = uri
            self.uris[uri.lower()] = self.nodes[oid]
    def loadNrs(self):
        # casting to varchar to convert to decimal without float problems
        if self.nrs: return
        SQL = "SELECT objectid, cast(nr as varchar(255)) from ont_objects"
        for oid, nr in self.db.doQuery(SQL):
            nr = str2nr(nr)
            n = self.nodes.get(oid)
            if not n: continue
            n._nr = nr
            if nr:
                if nr in self.nrs: raise Exception("Duplicate nr: %s" % nr)
                self.nrs[nr] = n
    def getNodeByURI(self, uri, strict=True):
        self.loadURIs()
        if strict:
            return self.uris[uri.lower()]
        else:
            return self.uris.get(uri.lower())
    def getNodeByLabel(self, label, strict=True):
        if strict:
            return self.labels[label.lower()]
        else:
            return self.labels.get(label.lower())
    def getRoots(self):
        for n in self.nodes.values():
            if type(n) == Class:
                if not list(n.getParents()):
                    yield n

_cache = {}
def fromDB(db):
    if db in _cache: return _cache[db]
    o = Ontology(db)
    _cache[db] = o
    SQL = """SELECT o.objectid, label, ontologyid FROM ont_objects o
          INNER JOIN ont_instances i on o.objectid = i.objectid"""
    for oid, label, ontid in db.doQuery(SQL):
        o.addNode(Instance(o, oid, label, ontid))
    SQL = """SELECT o.objectid, label, ontologyid FROM ont_objects o
          INNER JOIN ont_classes c on o.objectid = c.objectid"""
    for oid, label,ontid in db.doQuery(SQL):
        o.addNode(Class(o, oid, label, ontid))
    SQL = "SELECT superclassid, subclassid FROM ont_classes_subclasses"
    for sup, sub in db.doQuery(SQL):
        sup = o.nodes[sup]
        sub = o.nodes[sub]
        sup.addSubclass(sub)
    SQL = "SELECT classid, instanceid FROM ont_classes_instances"
    for c, i in db.doQuery(SQL):
        c = o.nodes[c]
        i = o.nodes[i]
        c.addInstance(i)
    SQL = """SELECT o.objectid, label, domainid, rangeid, temporal, ontologyid
          FROM ont_objects o INNER JOIN ont_predicates p 
          ON o.objectid = p.objectid"""
    for oid, label, d, r, temp, ontid in db.doQuery(SQL):
        d = o.nodes[d]
        r = o.nodes[r] if r else None
        o.addNode(Predicate(d, r, temp, o, oid, label, ontid))
    SQL = "SELECT role_subjectid, role_objectid, predicateid FROM ont_relations"
    for rs, ro, p in db.doQuery(SQL):
        rs = o.nodes[rs]
        ro = o.nodes[ro]
        p = o.nodes[p]
        rs.addRelation(p, ro)
    SQL = "SELECT role_subjectid, predicateid, [value] FROM ont_literals"
    for rs, p, val in db.doQuery(SQL):
        rs=o.nodes[rs]
        p=o.nodes[p]
        rs.setLiteral(p, val)
    SQL = """SELECT o.objectid, label, role_subjectid, role_objectid, predicateid, datefrom, dateto 
          FROM ont_objects o INNER JOIN ont_roles p 
          ON o.objectid = p.objectid"""
    for oid, label, rs, ro, p, df, dt in db.doQuery(SQL):
        p = o.nodes[p]
        rs = o.nodes[rs]
        ro = o.nodes[ro]
        o.addNode(Role(rs, p, ro, df, dt,o, oid, label))
    return o

def createNode(db, label, ontologyid, ver, nr=None, isinstance=True, languageid=2):
    oid = db.insert("on_objects", dict(created_version=ver))
    db.insert("on_nodes", dict(objectid=oid, created_version=ver, number=nr, isinstance=isinstance, ontologyid=ontologyid), retrieveIdent=False)
    db.insert("on_labels", dict(objectid=oid, languageid=languageid, created_version=ver, label=label), retrieveIdent=False)
    return oid

def createClass(db, label, ontologyid, ver, nr=None, superclass=None):
    oid = createNode(db, label, ontologyid, ver, nr, isinstance=False, languageid=2)
    if superclass:
        if isinstance(superclass, Node): superclass = superclass.oid
        db.insert("on_hierarchy", dict(parentid=superclass, childid=oid, created_version=ver), retrieveIdent=False)
    return oid


def createInstance(db, label, ontologyid, ver, nr=None, clas=None, languageid=2):
    oid = createNode(db, label, ontologyid, ver, nr, isinstance=True, languageid=languageid)
    if clas:
        if isinstance(clas, Node): clas = clas.oid
        db.insert("on_hierarchy", dict(parentid=clas, childid=oid, created_version=ver), retrieveIdent=False)
    return oid

def createRole(db, label, su, rel, obj, dfrom=None, dto=None,ver=None):
    db.insert("on_relations", dict(subjectid=su, objectid=obj,
                                    predicateid=rel, fromdate=dfrom, todate=dto, created_version=ver),
              retrieveIdent=False)

def createRelation(db, su, rel, obj, ver):
    db.insert("on_relations", dict(subjectid=su, predicateid=rel, objectid=obj, created_version=ver),
              retrieveIdent=False)

def getInstance(db, label, classid=None):
    sql = "select objectid from ont_objects where label = %s and objectid in (select objectid from ont_instances) " % toolkit.quotesql(label)
    if classid: sql += " and objectid in (select instanceid from ont_classes_instances where classid=%i)" % classid
    return db.getValue(sql)
    
def deleteNode(db, oid):
    db.doQuery("delete from on_labels where objectid = %i" % oid)
    db.doQuery("delete from on_hierarchy where parentid = %i" % oid)
    db.doQuery("delete from on_hierarchy where childid = %i" % oid)
    db.doQuery("delete from on_relations where objectid = %i" % oid)
    db.doQuery("delete from on_relations where subjectid = %i" % oid)
    db.doQuery("delete from on_nodes where objectid = %i" % oid)
    db.doQuery("delete from on_objects where objectid = %i" % oid)
                

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.anokoDB()
    o = fromDB(db)
    for n in o.nodes.values():
        if 'enior' in n.label:
            print n.label
