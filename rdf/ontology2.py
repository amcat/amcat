from pySesame2 import Output
from uri import *
import sys, toolkit, types

class Node(object):
    def __init__(self, ontology, uri):
        self.ontology = ontology
        self.uri = uri
        self.label = None
        self.description = None

    def changeTo(self, clas):
        if self.__class__ == clas: return
        if self.__class__ <> Node:
            raise Exception("Node types are disjoint! Trying to change %s from %s into %s" % (self.uri, self.__class__, clas))
        self.__class__ = clas
        self.__init__()
    def __str__(self):
        return "[%s %s]"% (type(self).__name__, self.label or self.uri)
    def shorturi(self):
        return self.ontology.sesame.nscollapse(self.uri)
    def walk(self, depth = 0, maxDepth=None):
        if maxDepth is not None and depth >= maxDepth: return
        children = list(self.getChildren())
        children.sort(lambda x,y: cmp(x[1].label, y[1].label))
        for r,c in children:
            #prune children that also appear deeper in the tree
            if c.hasAncestor(self, indirectOnly=True): continue
            yield (depth, self, r, c)
            for info in c.walk(depth + 1, maxDepth=maxDepth):
                yield info
    def getAncestors(self, indirectOnly=False, date=None):
        for (rel, parent) in self.getParents(date):
            if not indirectOnly: yield parent
            for ancestor in parent.getAncestors(indirectOnly=False, date=date):
                yield ancestor
    def hasAncestor(self, who, indirectOnly=False, date=None):
        for anc in self.getAncestors(indirectOnly, date=date):
            if anc == who: return True
        return False
    def hasDescendant(self, filter):
        children = list(self.getChildren())
        for r,child in children:
            if filter(child): return True
        for r,child in children:
            if child.hasDescendant(filter): return True
        return False
    def getNumber(self):
        if 'number' in dir(self): return self.number
        return None
        

class Instance(Node):
    def __init__(self):
        self.classes = set()
        self.outgoing = set()
        self.incoming = set()
        self.literals = {} # predicate : value
    def addClass(self, clas):
        clas.addInstance(self)
    def getOutgoing(self, predicate):
        return set(x.object for x in self.outgoing if x.predicate == predicate)
    def getIncoming(self, predicate):
        return set(x.subject for x in self.incoming if x.predicate == predicate)
    def getLiteral(self, predicate):
        if type(predicate) in types.StringTypes:
            if predicate in self.ontology.nodes:
                predicate = self.ontology.nodes[predicate]
            else:
                uri = self.ontology.sesame.nsexpand(predicate)
                if uri in self.ontology.nodes:
                    predicate = self.ontology.nodes[uri]
        return self.literals.get(predicate, None)
    def getChildren(self, date=None):
        for role in self.incoming:
            if date:
                if role.rfrom and role.rfrom > date: continue
                if role.rto and role.rto <= date: continue
            yield (role.predicate, role.subject)
    def getParents(self, date=None):
        for clas in self.classes:
            yield ("rdf:type", clas)
        for role in self.outgoing:
            if date:
                if role.rfrom and role.rfrom > date: continue
                if role.rto and role.rto <= date: continue
            yield (role.predicate, role.object)

    
class Class(Node):
    def __init__(self):
        self.supers = set()
        self.subs = set()
        self.instances = set()
        self.outgoing = set()
        self.incoming = set()

    def addInstance(self, inst):
        inst.classes.add(self)
        self.instances.add(inst)
    def addSubclass(self, clas):
        clas.supers.add(self)
        self.subs.add(clas)
    def getChildren(self, date=None):
        for sub in self.subs:
            yield ("rdfs:subClassOf", sub)
        for inst in self.instances:
            #hack! voorkomt dat een subissue zowel onder zn superissue als onder issue hangt
            #if not inst.outgoing:
            yield ("rdf:type", inst)
    def getParents(self, date=None):
        for super in self.supers:
            yield ("rdfs:subClassOf", super)
    
class Role(Node):
    def __init__(self):
        self.subject = None
        self.predicate = None
        self.object = None
        self.rfrom = None
        self.rto = None
    def setSubject(self, subject):
        self.subject = subject
        subject.outgoing.add(self)
    def setObject(self, object):
        self.object = object
        object.incoming.add(self)
    def setPredicate(self, pred):
        self.predicate = pred
        pred.instances.add(self)
    def setFrom(self, rfrom):
        self.rfrom = rfrom
    def setTo(self, rto):
        self.rto = rto
    def __str__(self):
        return "<Role %s/%s/%s>" % (self.subject.label, self.predicate.label, self.object.label)

class Predicate(Node):
    def __init__(self):
        self.instances = set()
        self.domain = None
        self.range = None
        self.role = False
        self.literal = False
    def setRange(self, range):
        self.range = range
        range.incoming.add(self)
    def setDomain(self, domain):
        self.domain = domain
        domain.outgoing.add(self)

class Ontology(object):
    def __init__(self, sesame):
        self.sesame = sesame
        self.nodes = {} # {uri : Node}
    def get(self, uri, clas = None, newok=False):
        if uri not in self.nodes:
            if not newok: return None
            self.nodes[uri] = Node(self, uri)
        node = self.nodes[uri]
        if clas: node.changeTo(clas)
        return node
    def getInstance(self, uri, newok=False): return self.get(uri, Instance, newok)
    def getClass(self, uri, newok=False): return self.get(uri, Class, newok)
    def getRole(self, uri, newok=False): return self.get(uri, Role, newok)
    def getPredicate(self, uri, newok=False): return self.get(uri, Predicate, newok)
    def nsexpand(self, uri):
        return self.sesame.nsexpand(uri)
    def getRoots(self):
        for node in self.nodes.values():
            if type(node) == Class and not node.supers:
                yield node

inspect = set((
#    "amcat:roleSubject",
#    "k06:kenobj-5033324-koserkayatk",
#    "k06:role-6754-dupuis1k-memberOfParty-vvd",
#    "k06:kenobj-501-regering",
#    "k06:partOfDept",
#    "rdfs:subPropertyOf",
    ))

def fromSesame(rdfdb):
    """Create an Ontology object from sesame

    On the first pass, query all 'structural' predicates and build the
    classes, instances etc. On the second pass, query all other
    predicates and build the properies.

    """
    def debug(*uris):
        print "\t".join(rdfdb.nscollapse(x) for x in uris)
    ont = Ontology(rdfdb)

    firstpass = RDF_TYPE,RDFS_SUBPROPERTYOF,RDFS_SUBCLASSOF,RDFS_LABEL,RDFS_COMMENT,AMCAT_NUMBER,AMCAT_ROLESUBJECT,AMCAT_RANGE,AMCAT_DOMAIN, AMCAT_ROLEFROM, AMCAT_ROLETO
    where = " OR ".join("Y="+rdfdb.nscollapse(x) for x in firstpass)
    data = rdfdb.execute("SELECT X,Y,Z from {X} Y {Z} WHERE (%s)" % where)

    for s,p,o in data:
        for x in s,p,o:
            if rdfdb.nscollapse(x) in inspect: debug(s,p,o)
        if p == RDF_TYPE:
            #debug(s,p,o)
            if o == AMCAT_ROLE_INSTANCE:
                ont.getRole(s,newok=True)
            elif o == RDFS_CLASS:
                ont.getClass(s,newok=True)
            elif o == RDF_PROPERTY:
                ont.getPredicate(s,newok=True)
            else:
                s = ont.getInstance(s,newok=True)
                o = ont.getClass(o,newok=True)
                o.addInstance(s)
        elif p == RDFS_SUBPROPERTYOF:
            if o == AMCAT_ROLE:
                ont.getPredicate(s,newok=True).role = True
            elif o == AMCAT_LITERALPROPERTY:
                ont.getPredicate(s,newok=True).literal = True
        elif p == RDFS_SUBCLASSOF:
            s = ont.getClass(s,newok=True)
            o = ont.getClass(o,newok=True)
            o.addSubclass(s)
        elif p == RDFS_LABEL:
            ont.get(s,newok=True).label = o
        elif p == RDFS_COMMENT:
            ont.get(s,newok=True).description = o 
        elif p == AMCAT_NUMBER:
            ont.get(s,newok=True).number = o
        elif p == AMCAT_ROLESUBJECT:
            o = ont.getInstance(o,newok=True)
            s = ont.getRole(s,newok=True)
            s.setSubject(o)
        elif p == AMCAT_RANGE:
            s = ont.getPredicate(s,newok=True)
            o = ont.getClass(o,newok=True)
            s.setRange(o)
        elif p == AMCAT_DOMAIN:
            s = ont.getPredicate(s,newok=True)
            o = ont.getClass(o,newok=True)
            s.setDomain(o)
        elif p == AMCAT_ROLEFROM:
            #debug(s,p)
            s = ont.getRole(s,newok=True)
            s.setFrom(o)
        elif p == AMCAT_ROLETO:
            s = ont.getRole(s,newok=True)
            s.setTo(o)
        else:
            raise Exception("Should never get here!")

    where = " AND ".join("Y!="+rdfdb.nscollapse(x) for x in firstpass)
    data = rdfdb.execute("SELECT X,Y,Z from {X} Y {Z} WHERE (%s)" % where)

    i = 0
    for s,p,o in data:
        pold = p
        p = ont.getPredicate(p)
        if not p:
            print >>sys.stderr, "%s --> %s" % (pold, p)
        
        if p.role:
            o = ont.getInstance(o)
            s = ont.getRole(s)
            s.setPredicate(p)
            s.setObject(o)
        elif p.literal:
            s = ont.getInstance(s)
            s.literals[p] = o
            
        else:
            o = ont.getInstance(o)
            s = ont.getInstance(s)
            role = ont.getRole("blank:%i"%i, newok=True)
            i+=1
            role.setPredicate(p)
            role.setSubject(s)
            role.setObject(o)
    return ont

_PICKLE_FILE="/tmp/ontology-%s.cache"
def fromPickle(rdfdb=None, file=None, reset=False):
    import sys, os.path, cPickle
    sys.setrecursionlimit(4000)
    ont = None
    if not file:
        if rdfdb:
            file = _PICKLE_FILE % rdfdb.repo
        else:
            file = _PICKLE_FILE % ""
    if not reset and os.path.exists(file):
        try:
            ont = cPickle.load(open(file))
        except IOError, e:
            if not rdfdb: raise e
            toolkit.warn(e)
    if rdfdb and not ont:
        print "REquerying ontology..." 
        ont = fromSesame(rdfdb)
        cPickle.dump(ont, open(file, 'w'))      
    return ont
    
    

if __name__ == '__main__':
    import pySesame2, types
    rdfdb = pySesame2.connect()
    ont = fromPickle(rdfdb)
    for root in ont.getRoots():
        print root.label
        for depth, node, r, c in root.walk():
            if type(r) not in types.StringTypes:
                r = r.label
            instance = 'Instance' in `type(c)`
            c = c.label
            r,c = map(lambda x:x.encode("ascii", "replace"), (r,c))
            print "%s%s|%s|%s" % ("\t"*(depth+1), c, instance, r)
    
