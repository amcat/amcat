import StringIO

"""
Classes that define a graph as a set of parent - relation - child triples
"""

class Graph(object):
    """Class that defines a graph as a sequence of (parent, relation, child) triples
    Subclasses/users should either call __init__ with triples, provide a triples attribute,
    _or_ subclass the getTriples() method.
    This class should (at some point) provide the graph functionality for
    parse trees, NET sentences, ontology, etc."""
    
    def __init__(self, triples=None):
        if triples is not None:
            self.triples = triples
    def getTriples(self):
        return self.triples
    def getRoot(self):
        first = None
        for node in self.getNodes():
            if first is None: first = node
            if not node.parentNode:
                return node
        if not first:
            raise Exception("Tree %r has no root?" % self)
        return first
        
    def getNodes(self, astree=False):
        if astree: # start with root, depth first
            stack = [self.getRoot()]
            seen = set(stack)
            while stack:
                n = stack.pop(0)
                yield n
                for n2 in n.childNodes:
                    if n2 in seen: continue
                    stack.append(n2)
                    seen.add(n2)
                    
        else:# in order of appearance
            seen = set()
            for parent, rel, child in  self.getTriples():
                for node in parent, child:
                    if node not in seen: yield node
                    seen.add(node)
            
 
    def printNetworkxGraph(self, *args, **kargs):
        return printNetworkxGraph(self, *args, **kargs)
    
class Node(object):
    def __init__(self, graph=None):
        self.graph = graph

    def getGraph(self):
        return self.graph
    
    @property
    def childNodes(self):
        for child, rel in self.children:
            yield child
    @property
    def parentNodes(self):
        for parent, rel in self.parents:
            yield parent
    @property
    def children(self):
        for parent, rel, child in self.getGraph().getTriples():
            if parent == self:
                yield child, rel
    @property
    def parents(self):
        for parent, rel, child in self.getGraph().getTriples():
            if child == self:
                yield parent, rel
    @property
    def parent(self):
        "In a tree, a single parent is useful"
        for parent, rel  in self.parents: return parent, rel
    @property
    def parentNode(self):
        "In a tree, a single parent is useful"
        for parent in self.parentNodes: return parent

    def getDescendants(self, stoplist=set()):
        yield self
        stoplist.add(self)
        for child in self.childNodes:
            if child in stoplist: continue
            for desc in child.getDescendants(stoplist):
                yield desc

def getAttr(obj, attr):
    try:
        return obj.__getattribute__(attr)
    except AttributeError:
        return None

def getNxLabel(node):
    s = getattr(node, "graphlabel", str(node))
    return s

def getNxAttributes(node):
    attrs = {}
    color, alpha, shape, size = [getattr(node, x, None) for x in ("graphcolor","graphalpha","graphshape", "graphsize")]
    if color: attrs['node_color'] = color
    if alpha: attrs['alpha'] = alpha
    if size: attrs['node_size'] = size
    if shape:
        if shape == 'rect': attrs['node_shape']=([[-2.0, -1.0], [-2.0, 1.0], [2.0, 1.0], [2.0, -1.0]], 0)
        else: attrs['node_shape'] = shape
    return attrs
    
def printNetworkxGraph(graph, output=None):
    import networkx
    import matplotlib.pyplot as plt
    plt.clf()
    plt.figure(figsize=(10,10))

    
    labels = {}
    edgelabels = {}
    g = networkx.DiGraph()
    for parent, relation, child in graph.getTriples():
        g.add_edge(parent, child)
        labels[parent] = getNxLabel(parent)
        labels[child] = getNxLabel(child)
        edgelabels[child, parent] = str(relation)
    pos=networkx.graphviz_layout(g,prog='dot')
    pos = dict((k, (x*50,y*50)) for (k,(x,y)) in pos.items())


    for node in graph.getNodes():
        attrs = getNxAttributes(node)
        if attrs:
            networkx.draw_networkx_nodes(g, pos, nodelist=[node], **attrs)
    
    networkx.draw_networkx_edges(g, pos, width=1,alpha=0.2,edge_color='b')

    networkx.draw_networkx_labels(g,pos,labels,font_size=9)
    networkx.draw_networkx_edge_labels(g, pos, edge_labels=edgelabels, font_size=7)

    plt.axis('off')
    if output:
        return plt.savefig(output)
    else:
        s = StringIO.StringIO()
        plt.savefig(s, format="png")
        return s.getvalue()
