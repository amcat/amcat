import os, sys, toolkit, base64

def printError(name, msg):
    toolkit.warn(msg)

class Node(object):
    def __init__(self, id, label=None):
        self.id = id
        self.attrs = {}
        if label: self.attrs['label'] = label
        self.style = {}
    def getID(self):
        return '"%s"' % self.id
    def getDot(self):
        a = dotattrs(self.attrs, self.style)
        return '%s [%s];' % (self.getID(), a)

class Edge(object):
    def __init__(self, subj, obj, label=None):
        self.subj = subj
        self.obj = obj
        self.attrs = {}
        if label: self.attrs['label'] = label
        self.style = {}
    def getDot(self):
        a = dotattrs(self.attrs, self.style)
        return '%s -> %s [%s];' % (self.subj.getID(), self.obj.getID(), a)
    def setlinewidth(self, w):
        self.style['setlinewidth'] = w
    def setcolor(self, h,s ,b):
        self.attrs['color'] = "%1.4f,%1.4f,%1.4f" % (h,s,b)
    def setlabel(self, label):
        self.attrs['label'] = label


def dotattrs(attrs, style):
    if style:
        attrs['style'] = ",".join("%s(%s)" % i for i in style.items())
    return ",".join('%s="%s"' % i for i in attrs.items())

class Graph(object):
    def __init__(self):
        self.nodes = {} # id : Node
        self.edges = {} # subjNode, objNode : Edge

    def addNode(self, node, **kargs):
        if type(node) <> Node:
            node = Node(node, **kargs)
        self.nodes[node.id] = node
        return node

    def getNode(self, nodeid, create=True, **kargs):
        if nodeid in self.nodes:
            return self.nodes[nodeid]
        if create:
            return self.addNode(nodeid, **kargs)

    def addEdge(self, subj, obj, **kargs):
        if type(subj) <> Node: subj = self.getNode(subj)
        if type(obj) <> Node: obj = self.getNode(obj)
        edge = Edge(subj, obj, **kargs)
        self.edges[subj, obj] = edge
        return edge

    def getDot(self):
        entries = []
        for node in self.nodes.values():
            entries.append(node.getDot())
        for edge in self.edges.values():
            entries.append(edge.getDot())
        return "digraph G {\n%s\n}" % ("\n".join(e for e in entries if e))

    def getImage(self, *args, **kargs):
        return dot2img(self.getDot(), *args, **kargs)
    def getHTMLObject(self):
        return dot2object(self.getDot())
    def getHTMLDoc(self):
        return '<html><body><p>%s</p><pre>%s</pre></body></html>' % (self.getHTMLObject(), self.getDot())

def dot2img(dot, format="jpg", errListener = printError):
    cmd = 'dot -T%s' % format
    img, err = toolkit.execute(cmd, dot, listener=errListener)
    return img

def dot2object(dot):
    png = dot2img.getImage(dot, format="png")
    data = base64.b64encode(png)
    return "<object type='image/png' data='data:image/png;base64,%s'></object>" % data


if __name__ == '__main__':
    g = Graph()

    g.addEdge("a", "b", label="+1")
    g.addEdge("a", "c").label = "-1"
    n = Node("d", "dirk")
    g.addNode(n)
    g.addEdge(n, "b")
    g.getNode("b", create=False).label="boer"

    print g.getImage(format="png")
    
    #print dot2img(dot)
