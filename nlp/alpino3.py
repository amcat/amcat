import xml.sax.handler, xml.sax
import types
import lemma
from toolkit import execute, warn

class Pos:
    def __init__(self, posstr, spec=""):
        if spec or "(" not in posstr:
            self.major, self.minor = posstr, spec
        else:
            if len(posstr.split("(", 1)) <> 2: print `posstr`
            self.major, spec = posstr.split("(", 1)
            self.minor = spec[:-1].split(",")

class Node:
    def __init__(self, sentence, begin, lemma):
        self.sentence = sentence
        self.lemma = lemma
        self.children = {}
        self.parents = {}
        self.begin = begin

    def addchild(self, child, rel):
        self.children[rel] = self.children.get(rel, set()) | set([child])
        child.parents[rel] = child.parents.get(rel, set()) | set([self])

    def prnt(self, indent="", rel="", blacklist=set()):
        if rel: rel = "(%s) " % rel
        print "%s%s%s %s" % (indent, rel, self.lemma.lemmaid, self.lemma.getLemma())
        if self in blacklist:
            print "%s  ..." % indent
            return
        blacklist.add(self)
        for rel, child in self.getchildren(True):
            child.prnt(indent+"  ", rel, blacklist)

    def getchildren(self, includerel = False):
        for rel, children in self.children.items():
            for child in children:
                if includerel:
                    yield rel, child
                else:
                    yield child
                    
    def getparents(self, includerel = False):
        for rel, parents in self.parents.items():
            for parent in parents:
                if includerel:
                    yield rel, parent
                else:
                    yield parent

class Sentence:
    def __init__(self):
        self.nodeindex = {}

    def get(self, nodeid, *args, **kargs):
        return self.nodeindex.get(nodeid, None)

    def add(self, node, nodeid):
        if nodeid in self.nodeindex: raise Exception("Node %s already exists!" % nodeid)
        self.nodeindex[nodeid] = node

    def prnt(self):
        for root in self.roots():
            root.prnt()

    def roots(self):
        roots = set()
        for node in self.nodeindex.values():
            if not node.parents:
                roots.add(node)
        return roots

    def dot(self, nodedefs = {}):
        rels, nodes = [], []
        style= 'graph [rankdir="TB",ranksep="0"];edge[dir="back",arrowsize=".4",fontsize="10",fontcolor="1,0,.4",fontname="arial"];node[fontname="arial",fontsize="9",height=".2",shape="box",color="1,0,1"]'
        def id(node): return "%s_%i" % (node.lemma, node.begin)
        for node in self.nodeindex.values():
            nstyle = {'label' : "%s\\n(%s)" % (node.lemma, node.pos.major)}
            nstyle.update(nodedefs.get(node.begin, {}))
            nodedef = ",".join('%s="%s"' % ab for ab in nstyle.items())
            nodes.append('"%s" [%s];' % (id(node), nodedef))
            for rel, child in node.getchildren(True):
                rels.append('"%s" -> "%s" [label="%s"];' % (id(node), id(child), rel))
        dot = "digraph G{\n%s\n\n%s\n\n%s\n}" % (style, "\n".join(nodes), "\n".join(rels))
        return dot
                       

    def nodes(self):
        visited = set()

        stack = list(self.roots())
        while stack:
            node = stack.pop(0)
            if node in visited: continue
            visited.add(node)
            yield node
            stack += list(node.getchildren())
    
def fromdb(db, sid):
    sql = """select wordbegin, words_lemmaid
             from vw_parses_words where sentenceid = %i""" % sid
    s = Sentence()
    for b,l in db.doQuery(sql):
        lem = lemma.Lemma(l, db)
        node = Node(s, b, lem)
        s.add(node, b)
        
    sql = """select t.parentbegin, t.childbegin, r.name
             from parses_triples t inner join parses_rels r on t.relation = r.relid
             where sentenceid=%i """ % sid

    for p, c, rel in db.doQuery(sql):
        pn = s.get(p)
        cn = s.get(c)
        pn.addchild(cn, rel)
        
    return s

        
        

################## AUXILLIARY FUNCTIONS ####################

def _isString(obj):
    return type(obj) in types.StringTypes

################## TEST DRIVER METHOD ######################
    
if __name__ == '__main__':
    import sys, dbtoolkit
    db = dbtoolkit.anokoDB()
    s = fromdb(db, int(sys.argv[1]))
    s.prnt()
    
