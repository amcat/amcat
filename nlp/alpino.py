import xml.sax.handler, xml.sax
import types
from toolkit import execute, warn

ALPINO = "/home/amcat/resources/Alpino"

class Pos:
    def __init__(self, main, major, minor):
        self.main = main
        self.major = major
        self.minor = minor

class Node:
    def __init__(self, begin, word, lemma, pos):
        self.word = word
        self.lemma = lemma
        self.pos = pos
        self.children = {}
        self.parents = {}
        self.begin = begin
    def addchild(self, child, rel):
        self.children[rel] = self.children.get(rel, set()) | set([child])
        child.parents[rel] = child.parents.get(rel, set()) | set([self])

    def prnt(self, indent="", rel="", blacklist=set()):
        if rel: rel = "(%s) " % rel
        print "%s%s%s (%s / %s / %s)" % (indent, rel, self.word,self.lemma, self.pos.major, self.pos.minor)
        if self in blacklist:
            print "%s  ..." % indent
        else:
            blacklist.add(self)
            for rel, child in self.getchildren(True):
                child.prnt(indent+"  ", rel,blacklist)

    def __str__(self):
        return "%s (%s / %s / %s)" % (self.word,self.lemma, self.pos.major, self.pos.minor)

    def getchildren(self, includerel = False):
        for rel, children in self.children.items():
            for child in children:
                if includerel:
                    yield rel, child
                else:
                    yield child
                

class Sentence:
    def __init__(self):
        self.nodeindex = {}

    def get(self, nodeid, *args, **kargs):
        return self.nodeindex.get(nodeid, None)

    def add(self, node, nodeid):
        if nodeid in self.nodeindex: raise Exception("Node %s already exists!" % nodeid)
        self.nodeindex[nodeid] = node

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

    def prnt(self):
        for root in self.roots():
            root.prnt()
    
def fromFullTriples(str):
    result = Sentence()
    def getnode(begin,word, lemma, pos, pos2, pos3):
        res = result.get(begin)
        if not res:
            if "(" in pos3:
                major, minor = pos3.split("(",1)
                minor = minor[:-1]
            else:
                major, minor = pos3,""
            pos = Pos(pos, major, minor)
            res = Node(begin, word, lemma, pos)
            result.add(res, begin)
        return res
    if _isString(str): str = str.split("\n")
    for line in str:
        if not line.strip(): continue
        fields = line.strip().split("|")
        if len(fields) <> 16: raise Exception("Cannot parse %r" % fields)
        plem, pword, pbegin, pend, ppos, ppos2, ppos3, rel, clem, cword, cbegin, cend, cpos, cpos2, cpos3,sid = fields
        pnode = getnode(pbegin, pword, plem, ppos, ppos2, ppos3)
        cnode = getnode(cbegin, cword, clem, cpos, cpos2, cpos3)
        r1, rel = rel.split("/")
        pnode.addchild(cnode, rel)
        
    return result

def tokenize(sent, alpinohome=ALPINO, errhandler=warn):
    cmd = "%s/Tokenization/tok" % alpinohome
    if not sent: return None
    out, err = execute(cmd, sent+" ")
    print "%r -> %r" % (sent, out)
    if err and errhandler: errhandler(err)
    out = out.replace("\n"," ")
    return out

def parse(sent, alpinohome=ALPINO, errhandler=warn):
    cmd = "LD_LIBRARY_PATH=%s/create_bin ALPINO_HOME=%s %s/create_bin/Alpino demo=off end_hook=dependencies -parse" % (alpinohome, alpinohome, alpinohome)
    if not sent: return None
    #print cmd
    out, err = execute(cmd, sent)
    if err and errhandler: errhandler(err)
    #print out
    return out

def parseTriples(sent, alpinohome=ALPINO, errhandler=warn):
    out = parse(sent, alpinohome, errhandler)
    if not out: return None
    return fromFullTriples(out)

def fromdb(db, sid):
    sql = """select wordbegin, word, lemma, pos, major, minor 
             from vw_parses_words_pos where sentenceid = %i""" % sid
    s = Sentence()
    for b,w,l,p,mj,mn in db.doQuery(sql):
        pos = Pos(p, mj,mn)
        node = Node(b,w,l, pos)
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
    triples = dbtoolkit.anokoDB().getValue("SELECT parse FROM sentences_parses WHERE parsejobid>9 AND sentenceid=%i" % int(sys.argv[1]))
    s = fromFullTriples(triples)
    s.prnt()
