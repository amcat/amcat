class Node(object):
    def __init__(self, ont, oid, label):
        self.ont = ont
        self.oid = oid
        self.label = label
        self._uri = None
    def getURI(self):
        if not self._uri:
            self.ont.loadURIs()
        return self._uri
            

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
class Klass(Node):
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

class Predicate(Node):
    def __init__(self, domain, range, temporal, *args, **kargs):
        Node.__init__(self, *args, **kargs)
        assert isinstance(domain, Klass)
        assert (not range) or isinstance(range, Klass)
        self.domain = domain
        self.range = range
        self.temporal = temporal
        self.literal = not range
        assert not (self.literal and self.temporal)

class Ontology(object):
    def __init__(self, db):
        self.nodes = {} # oid : node
        self.labels = {} # label : node
        self.db = db
    def addNode(self, node):
        if node.label in self.labels: raise Exception("Duplicate label: %s" % node.label)
        if node.oid in self.nodes: raise Exception("Duplicate oid: %s" % node.oid)
        self.nodes[node.oid] = node
        self.labels[node.label] = node
    def loadURIs(self):
        SQL = "SELECT objectid, uri from ont_objects o"
        for oid, uri in self.db.doQuery(SQL):
            self.nodes[oid]._uri = uri
        

def fromDB(db):
    o = Ontology(db)
    SQL = """SELECT o.objectid, label FROM ont_objects o
          INNER JOIN ont_instances i on o.objectid = i.objectid"""
    for oid, label in db.doQuery(SQL):
        o.addNode(Instance(o, oid, label))
    SQL = """SELECT o.objectid, label FROM ont_objects o
          INNER JOIN ont_classes c on o.objectid = c.objectid"""
    for oid, label in db.doQuery(SQL):
        o.addNode(Klass(o, oid, label))
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
    SQL = """SELECT o.objectid, label, domainid, rangeid, temporal 
          FROM ont_objects o INNER JOIN ont_predicates p 
          ON o.objectid = p.objectid"""
    for oid, label, d, r, temp in db.doQuery(SQL):
        d = o.nodes[d]
        r = o.nodes[r] if r else None
        o.addNode(Predicate(d, r, temp, o, oid, label))
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

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.anokoDB()
    o = fromDB(db)
