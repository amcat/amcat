class State(object):
    """
    The State of the data tabulation/aggregation algorithm consisting of
    Nodes and Edges. Initially, Nodes and Edges correspond to Fields and Mappings,
    but as Operations are applied the state is reduced by combining different Nodes
    to form Nodes consisting of multiple Fields. 
    """
    def __init__(self, tabulator, mappings, filters):
        """
        mappings is a list of Mapping objects representing the initial state
        filters {field: list-of-values} are seen as a priori data structures on the nodes
        """
        self.tabulator = tabulator
        self.edges = set(mappings2edges(mappings, filters))
        self.solution = None
    def collapse(self, oldedge, newnode):
        """
        Removes the given Edge oldedge from this state, replacing its nodes
        by the given Node newnode. Removing the last edge will set the solution
        variable to the data of the newnode.
        """
        self.edges.remove(oldedge)
        if not self.edges or not newnode.data:
            self.solution = newnode
        else: # Replace references to old nodes, by reference to new node
            oldnodes = [oldedge.a, oldedge.b]
            for edge in self.edges:
                if edge.a in oldnodes:
                    edge.a = newnode
                if edge.b in oldnodes:
                    edge.b = newnode
        self.tabulator.clean(self, newnode)
    def getNodes(self):
        nodes = set()
        for edge in self.edges: nodes |= set([edge.a, edge.b])
        return nodes
    def getEdges(self, fromnode):
        for edge in self.edges:
            if edge.a == fromnode:
                yield edge
    def __len__(self):
        return len(self.edges)    


def mappings2edges(mappings, filters):
    nodes = {} # temp field -> Node map
    def getNode(field):
        if field not in nodes:
            flters = [[x] for x in filters[field]] if field in filters else None
            nodes[field] = Node([field], flters)
        return nodes[field]
    for mapping in mappings:
        yield Edge(
            getNode(mapping.a),
            getNode(mapping.b),
            mapping)

class Node(object):
    """
    Class Node contains a list of Field objects and a list of data
    A Node is connected to other nodes by NodeMappings
    """
    def __init__(self, fields, data=[]):
        self.fields = fields # list of Field objects
        self.data = data # list of tuple of data
    def getFields(self):
        return self.fields
    def  __str__(self):
        return "Node(%r, %r)" % (self.fields, self.data)
    __repr__ = __str__

class Edge(object):
    """
    An edge is an edge between two Nodes, corresponding to a mapping between fields in these nodes 
    """
    def __init__(self, a, b, mapping):
        """create an Edge between nodes 'a' and 'b' corresponding to the given mapping
        This fields of this mapping should exist in the Nodes a and b"""
        self.a = a
        self.b = b
        self.mapping = mapping
    def __str__(self):
        return "Edge(%r,%r)" % (self.a, self.b)
    __repr__ = __str__
            
