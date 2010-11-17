import networkx
from idlabel import IDLabel
import matplotlib.pyplot as plt
import StringIO
from networkx import *


############### AUX CLASSES ###################
class Word(IDLabel):
    def __init__(self, id, word, lemma):
        IDLabel.__init__(self, id, word)
        self.lemma = lemma

class Lemma(IDLabel):
    def __init__(self, id, lemma, pos):
        IDLabel.__init__(self, id, lemma)
        self.pos = pos

class Relation(IDLabel):
    def __init__(self, id, name):
        IDLabel.__init__(self, id, name)
        
_words, _lemmata = {}, {}
def getWord(wid, word, lemmaid, lemma, pos):
    if wid not in _words:
        if lemmaid not in _lemmata:
            _lemmata[lemmaid] = Lemma(lemmaid, lemma, pos)
        _words[wid] = Word(wid, word, _lemmata[lemmaid])
    return _words[wid]

_rels = None
def getRels(db):
    global _rels
    if _rels is None:
        _rels = {}
        for relid, name in db.doQuery("select relid, name from parses_rels"):
            _rels[relid] = name
    return _rels

############# PARSE TREE #####################

class ParseNode(IDLabel):
    def __init__(self, tree, word, position, data={}):
        IDLabel.__init__(self, position, word.label)
        self.tree = tree
        self.word = word
        self.position = position
        self.data = {}
    def getChildren(self):
        for dummy, child in self.tree.graph.out_edges(self):
            yield child
    def getRelations(self):
        for dummy, child in self.tree.graph.out_edges(self):
            d = self.tree.graph.get_edge_data(self, child)
            yield child, d.get("rel")
    def getParents(self):
        for parent, dummy in self.tree.graph.in_edges(self):
            d = self.tree.graph.get_edge_data(parent, self)
            yield parent, d.get("rel")
    def addData(self, key, value):
        self.data[key] = value
    def getRelation(self, other):
        for dummy, child in self.tree.graph.out_edges(self):
            if child == other:
                d = self.tree.graph.get_edge_data(self, child)
                return d.get('rel')
    def identity(self):
        return self.tree, self.position
    def __str__(self):
        return "%i:%s" % (self.position, self.word)
    def __repr__(self):
        return "ParseNode(%r, %r)" % (self.word, self.position)

    def getDescendants(self, stoplist=set()):
        yield self
        stoplist.add(self)
        for child in self.getChildren():
            if child in stoplist: continue
            for desc in child.getDescendants(stoplist):
                yield desc
    
    
class ParseTree(IDLabel):
    def __init__(self, id):
        IDLabel.__init__(self, id, str(id))
        self.graph = networkx.DiGraph()
    def addTriple(self, parent, child, rel):
        self.graph.add_edge(parent, child, rel=rel)

    def getNodes(self):
        """ Returns the tree nodes from root, breadth first """
        stack = [self.getRoot()]
        seen = set(stack)
        while stack:
            n = stack.pop(0)
            yield n
            for n2 in n.getChildren():
                if n2 in seen: continue
                stack.append(n2)
                seen.add(n2)

    def getNode(self, position):
        for node in self.graph.nodes():
            if node.position == position:
                return node
            
    def getRoot(self):
        for node in self.graph.nodes():
            if not self.graph.in_edges(node):
                return node
        for node in self.graph.nodes():
            if node.position == 0:
                return node
        raise Exception("No root! Sentence id %i " % self.id)

    def printTree(self, **kargs):
        kargs2 = dict(labelattr='label', edgelabelattr='getRelation')
        kargs2.update(kargs)
        return printGraph(self.graph,  **kargs2)

        
def fromDB(db, sid):
    SQL = "select wordbegin, wordid, word, lemmaid, lemma, pos from vw_parses_words where sentenceid = %i" % sid
    words = {}
    p = ParseTree(sid)
    rels = db.doQuery(SQL)
    if not rels: return
    for data in rels:
        i, wdata = data[0], data[1:]
        words[i] = ParseNode(p, getWord(*wdata), i)
    rels = getRels(db)
    SQL = "select parentbegin, childbegin, relation from parses_triples where sentenceid = %i order by childbegin" % sid
    for pb, cb, rel in db.doQuery(SQL):
        p.addTriple(words[pb], words[cb], rels[rel])
    return p

#################### Printing #######################

def getAttr(obj, attr):
    try:
        return obj.__getattribute__(attr)
    except AttributeError:
        return None

def printGraph(graph, output=None, labelattr="nx_label", edgelabelattr="nx_edgelabeler", nodeattr="nx_node_attributes"):
    plt.clf()
    plt.figure(figsize=(10,10))
    pos=graphviz_layout(graph,prog='dot')
    pos = dict((k, (x*50,y*50)) for (k,(x,y)) in pos.items())
    draw_networkx_edges(graph, pos, width=1,alpha=0.2,edge_color='b')

    labels = {}
    edgelabels = {}
    for n in graph.nodes():
        label = getAttr(n, labelattr)
        if label: labels[n] = label
        edgelabeler = getAttr(n, edgelabelattr)
        if edgelabeler:
            for n2 in graph.nodes():
                el = edgelabeler(n2)
                if el: edgelabels[n, n2] = el
        nodeattrs = getAttr(n, nodeattr)
        if nodeattrs:
            draw_networkx_nodes(graph, pos, nodelist=[n], **nodeattrs)

    draw_networkx_labels(graph,pos,labels,font_size=9)
    draw_networkx_edge_labels(graph, pos, edge_labels=edgelabels, font_size=7)

    plt.axis('off')
    if output:
        return plt.savefig(output)
    else:
        s = StringIO.StringIO()
        plt.savefig(s, format="png")
        return s.getvalue()
        
def getSentencePicture(db, sid):
    t = fromDB(db, sid)
    if not t: return
    return t.printTree()
        

############## DRIVER ######################

if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB()
    t = fromDB(db, 192)
    t.getRoot().nx_node_attributes = dict(color="r")
    t.printTree(output="/home/amcat/www-plain/test/test.png")
    
    
