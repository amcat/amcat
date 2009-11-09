from datasource import Field, Identity
import collections

class CombineTwoNodesOperation(object):    
    """
    Class CombineTwoNodesOperation can be used to combine two nodes, and does some extra magic
    
    Method "getUtility" returns the cheapest utility, if any. The result can be used for calculating the cheapes utility of a total state
    Method "apply" performs the actual combine action. It calls the combine function to do the magic, and calls the removeitems method of the state to update the state.
    """
    def __init__(self, nodea, nodeb, mapping):
        self.nodea = nodea
        self.nodeb = nodeb
        self.mapping = mapping
    def getUtility(self, state):
        u1 = len(self.nodea.data) * self.mapping.getCost(reverse=False) if self.nodea.data else None
        u2 = len(self.nodeb.data) * self.mapping.getCost(reverse=True)  if self.nodeb.data else None

        if u1 == None and u2 == None: return None
        if u1 == None: return u2
        if u2 == None: return u1 
        return max(-u1, -u2)
    def apply(self, state):
        
        print "apply state, old state"
        for node in  state.nodes:
            print node
        for mapping in state.mappings:
            print mapping
        newnode =  combine(self.nodea, self.nodeb, self.mapping)
        
        print newnode
#        return state - set([self.nodea, self.nodeb]) | set([newnode])
        state.removeItems(self.mapping, self.nodea, self.nodeb, newnode)

        print "apply state, new state"
        for node in  state.nodes:
            print node
            print node.data
        for mapping in state.mappings:
            print mapping
        
class OperationsFactory(object):
    """
    Method getOperations of class OperationsFactory returns all possible operations that can be applied to two nodes.
    The results are types of the class CombineTwoNodesOperation
    """
    def getOperations(self, state):
        for n1 in state.nodes:
            for n2, mapping in getMappings(state, n1):
                yield CombineTwoNodesOperation(n1, n2, mapping)
    
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
    def __repr__(self):
        return "<class: %s -> Fields: %s -- Data: %s>" % (self.__class__.__name__, self.fields, self.data)
    def __eq__(self, other):
        if other is None: return False
        if not isinstance(other, Node): return False
        return self.fields == other.fields
    __cmp__ = __eq__
    __str__ = __repr__

class NodeMapping(Identity):
    """
    A NodeMapping is a mapping between two nodes
    Nodes and nodemappings offer the possibility to combine nodes in a graph
    
    a and b are the end Nodes of the NodeMapping
    mapping is the parentmapping, which exists between Fields on a higher level. These Fields exist in the Fields list of the end Nodes
    getCost returns the cost to eliminate this mapping, and combine the nodes
    getNodes returns Node a and Node b
    """
    def __init__(self, a, b, mapping):
        Identity.__init__(self, a, b, mapping)
        self.a = a
        self.b = b
        self.mapping = mapping
    def getCost(self, reverse):
        return self.mapping.getCost(reverse)
    def getNodes(self):
        return [self.a,self.b]
    def __str__(self):
        return "node a: %s -- node b: %s -- parentmapping: %s" % ( self.a, self.b, self.mapping )
    __repr__ = __str__

def combineFieldMapping(nodea, nodeb):
    mapping = getMapping(nodea, nodeb)
    result = Node(nodea.fields + nodeb.fields)
    result.data = combinedata(mapping, nodea, nodeb)

def combineConceptMapping(nodea,nodeb):
    pass
    
def combine(nodea, nodeb, mapping):
    """
    The combine function combines the two nodes, over the mapping as supplied to this functio
    """
    
    # Get the parent mapping
    mapping = mapping.mapping

    # Get index of mapping in Fields list of node
    indexa = nodea.fields.index(mapping.a)
    indexb = nodeb.fields.index(mapping.b)
    
    # Walk over node in opposite direction, if node a not have data
    reverse = nodea.data is None
    if reverse:
        nodea, nodeb, indexa, indexb = nodeb, nodea, indexb, indexa
    
    
    newdata = []
    for arow in nodea.data:
        print "arow: " % arow
        mappedvalues = mapping.map(arow[indexa], reverse=reverse)
        for brow in findrows(nodeb.data, indexb, mappedvalues):
            print "brow: " % brow
            newdata.append(buildrow(arow, brow, reverse=reverse))
    
    newnode = Node(nodea.fields + nodeb.fields, newdata)
    return newnode

def buildrow(arow, brow, reverse=False):
    if reverse: 
        brow, arow = arow, brow
    return tuple(list(arow) + list(brow))

def findrows(data, index, values):
    if data is None:
        for val in values:
            yield [val]
    else:
        values = set(values)
        for row in data:
            if row[index] in values:
                yield row

def createNewNode(field):
    """
    Function createNewNode is used to create a new node with only one Field. It is a initial Node creation
    """
    newnode = Node([field])
    return newnode

class startState(object):
    """
    Class startstate is a class which creates in the constructor a state to start with before reducing the graph
    
    nodes is a list that contains all nodes that are mapped
    nodemappings is a list that contains all mappings between the nodes
    
    method removeItems removes the combined nodes from the list, and replaces these with a new node. Also it removes the mapping between the old nodes from the list.
    """
    def __init__(self, nodes, mappings, filters):
        newnodes = collections.defaultdict(Node)
        self.newnodes = []
        self.nodemappings = []
        def getNode(oldnode):
            if oldnode not in newnodes:
                dataindexes = []
                data = []
                if oldnode in filters.keys():
                    dataindexes.append(oldnode)
                    data.append(filters[oldnode])
                newnodes[oldnode] = Node([oldnode], data)
            return newnodes[oldnode]
        for mapping in mappings:
            na = getNode(mapping.a)
            nb = getNode(mapping.b)
            m = NodeMapping(na, nb, mapping)
            self.nodemappings.append(m)

        self.nodes = newnodes.values()
        self.mappings = mappings
        self.filters = filters
    def removeItems(self, oldmapping, nodea, nodeb, newnode):
        oldnodes = [nodea, nodeb]

        # Remove old mapping
        # --> iterate over list, and find index of mapping to remove
        # --> remove mappings by index in reversed order
        
        removeindices = []
        for mapping in self.nodemappings:
            if mapping == oldmapping:
                removeindices.append(self.nodemappings.index(mapping))
        removeindices.reverse()
        for index in removeindices:
            del self.nodemappings[index]

        # Replace references to old nodes, by reference to new node

        for mapping in self.nodemappings:
            if mapping.a in oldnodes:
                mapping.a = newnode
            if mapping.b in oldnodes:
                mapping.b = newnode

        # Remove old nodes
        # --> iterate over list, and find index of node to remove
        # --> remove nodes by index in reversed order
        
        removeindices = []
        for node in self.nodes:           
            if node in oldnodes:
                removeindices.append(self.nodes.index(node))
        removeindices.reverse()
        for index in removeindices:
            del self.nodes[index]

        # Append new node to list of nodes

        self.nodes.append(newnode)
    def __len__(self):
        return len(self.mappings)    
    
def getMappings(state, nodea):
    mappings = []
    for mapping in state.nodemappings:
        if nodea is mapping.a:
            yield mapping.b, mapping
            
class Aggregator(object):
    """
    Class Aggregator creates the actual aggregator object. The aggregator initiates itself with mappings and filters
    
    the getData method creates the graph, creates the nodes, creates a state, and reduces it until only data is left. The data will be returned.
    """
    def __init__(self, mappings, filters):
        self.mappings = mappings
        self.filters = filters
        self.nodes = []
    def getData(self):
        """
        filters = {concept : (values, )}
        returns data
        """
        self.operationsFactories = OperationsFactory()
        
        filtermappings = []

        print "create startstate"
        state = startState(self.nodes, self.mappings, self.filters) # state = collection nodes

        print state.filters.keys()

        for node in state.nodes:
            print "node, nodefield[0], state.filters.keys"
            print node
            print node.getFields()[0]
            
#            if node.getFields()[0] in state.filters.keys():
#                print state.filters[node.getFields()[0]]            
#                node.data[node.getFields()[0]] = state.filters[node.getFields()[0]]

        print "\n"

        for node in state.nodes:
            print node

        best = None
        print "best = none"
        for operation in self.operationsFactories.getOperations(state):
            print "operation:"
            print operation
            print operation.nodea
            print operation.nodeb
            print operation.mapping
            if best is None or operation.getUtility(state) > best.getUtility(state):
                best = operation
#            if not operation: raise Exception("!")
            print "best"
            print best
        state = best.apply(state)

#        mappings = getMappings(startstate, nodea, nodeb)
            
#        return list(state)[0].data