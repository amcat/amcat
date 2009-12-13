from tabulatorstate import Node
import toolkit
from itertools import izip

class Operation(object):
    """Interface for operations"""
    def getUtility(self, state):
        """Returns the utility of applying this operation to the given state"""
        abstract
    def apply(self, state):
        """Actually applies this operation on the state, returning an object
        representing the new state (possibly a reference to the old state modified
        'in place')"""
        abstract
        
class ReduceEdgeOperation(Operation):    
    """
    Class ReduceEdgeOperation can be used to combine two nodes along an edge
    to a single node containing the combined data
    """
    def __init__(self, edge):
        self.edge = edge
    def getUtility(self, state):
        """
        Utility is -1 times the lowest cost of traversing the mapping a->b or b->a
        """
        u1 = (-1 * len(self.edge.a.data) * self.edge.mapping.getCost(reverse=False)
               if self.edge.a.data else None)
        u2 = (-1 * len(self.edge.b.data) * self.edge.mapping.getCost(reverse=True)
               if self.edge.b.data else None)
        #toolkit.warn("Utility max(%s,%s)=%s for %s" % (u1, u2, max(u1, u2), self))
        return max(u1, u2)
    def apply(self, state):
        """
        Method "apply" performs the actual combine action. It calls
        the combine function to map the data, and calls the removeEdge
        method of the state to update the state.
        """
        toolkit.warn("Applying map %s" % str(self))
        newnode = combine(self.edge)
        state.collapse(self.edge, newnode)
        return state
    def __str__(self):
        return "Reduce(%s (%s) -> (%s) %s)" % (self.edge.a.fields, self.edge.a.data and len(self.edge.a.data), self.edge.b.data and len(self.edge.b.data), self.edge.b.fields)
    __repr__ = __str__
        
class OperationsFactory(object):
    """
    Factory to create possible operations on a state 
    """
    def getOperations(self, state):
        """
        Generate all operations that can be applied to a state.
        Currently returns a ReduceEdgeOperation for each edge
        """
        return map(ReduceEdgeOperation, state.edges)
       
def combine(edge):
    """
    The combine function combines t
    he two nodes of the given edge
    Returns a new node resulting from the combination
    """
    nodea, nodeb, mapping = edge.a, edge.b, edge.mapping
    if nodea.data is None and nodeb.data is None:
        raise Exception("No data! in mapping %s to %s" % (nodea, nodeb))
    
    # Get index of mapping in Fields list of node
    indexa = nodea.fields.index(mapping.a)
    indexb = nodeb.fields.index(mapping.b)
    
    # Traverse mapping in opposite direction, if node a does not have data
    reverse = nodea.data is None
    if reverse:
        nodea, nodeb, indexa, indexb = nodeb, nodea, indexb, indexa

    newdata = []

    memo = mapping.startMapping((arow[indexa] for arow in nodea.data), reverse=reverse)
    for arow in nodea.data:
        mappedvalues = mapping.map(arow[indexa], reverse=reverse, memo=memo)
        for brow in findrows(nodeb.data, indexb, mappedvalues):
            newdata.append(buildrow(arow, brow, reverse=reverse))
    
    if reverse: # undo reverse
        nodea, nodeb = nodeb, nodea
    newfields = nodea.fields + nodeb.fields
    return Node(newfields, newdata)

def buildrow(arow, brow, reverse=False):
    if reverse: 
        brow, arow = arow, brow
    return list(arow) + list(brow)

def findrows(data, index, values):
    if data is None:
        for val in values:
            yield [val]
    else:
        values = set(values)
        for row in data:
            if row[index] in values:
                yield row
