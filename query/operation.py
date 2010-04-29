from tabulatorstate import Node
import toolkit
from datasource import *
from itertools import izip
from amcatmetadatasource import DatabaseMapping
from dbtoolkit import quotesql

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

def getFields(edges):
    fields = {} # field : table
    for edge in edges:
        table = edge.mapping.getTable()
        fields[edge.mapping.a] = table
        fields[edge.mapping.b] = table
    return fields

def getJoins(fields):
    "Returns table join order [tablea, tableb, key] based on fields {field:table}"
    tables = set(fields.values())
    if len(tables) <= 1: return
    joins = {} # tableA, tableB -> key
    for field in fields:
        for a, b, key in field.getJoins():
            if a in tables and b in tables:
                if joins.get((a,b), key) <> key: raise Exception("?") 
                joins[a, b] = key
    included = set()
    jointos = set(b for (a,b) in joins)
    result = []
    while len(included) < len(tables):
        changed = False
        for a, b in joins: 
            key = joins[a,b]
            if (a,b,key) in result: continue
            if a in included or a not in jointos:
                included |= set((a,b))
                changed = True
                result.append((a,b,key))
                break
            if not changed:
                raise Exception("Cannot find join order!")
    return result

class DatabaseOperation(Operation):
    def __init__(self, edges):
        self.edges = edges
        self.db = toolkit.head(edges).mapping.a.datasource.db
    def getUtility(self, state):
        return 1
    
    def apply(self, state):
        fields = getFields(self.edges) # {field : table}

        fromstr = ""
        joins = getJoins(fields)
        if joins:
            for i, (a,b,key) in enumerate(joins):
                if not i: fromstr += a
                fromstr += "\n INNER JOIN %s ON %s.%s = %s.%s" % (b, a, key, b, key)
        else:
            fromstr = set(fields.values()).pop()
        sortedfields = sorted(fields.items())
        selectstr = ",".join("%s as v%i" % (f.getColumn(t), i)
                             for (i,(f,t)) in enumerate(sortedfields))
        
        wherestr = " AND ".join("(%s)" % f for f in getFilters(self.db, self.edges))
        distinctstr = " DISTINCT " if state.distinct else ""
        sql = "SELECT %s %s FROM %s WHERE %s" % (distinctstr, selectstr, fromstr, wherestr)

        toolkit.ticker.warn(`sql`)#[:100])
        data = self.db.doQuery(sql) or []
        fieldlist = [field[0] for field in sortedfields]
        result = mergeData(self.edges, fieldlist, data)

        state.collapse(self.edges, result)
        return state
    
    def __repr__(self):
        return "DBReduceAll(%s)" % ", ".join("%s->%s" % (e.mapping.a.column, e.mapping.b.column) for e in self.edges)

def mergeData(edges, fields, data):
    hooks = [] # list of (targetfield, old-node-fields, index-in-data, index-in-nodefieds, datamap, columnmap)
    processed = set()
    for e in edges:
        for field, node in ((e.mapping.a, e.a), (e.mapping.b, e.b)):
            if node not in processed and len(node.fields) > 1:
                processed.add(node)
                target = (set(node.fields) & set(fields)).pop()
                fi = fields.index(target)
                ti = node.fields.index(target)
                hookdata = collections.defaultdict(list)
                for row in node.data:
                    hookdata[row[ti]].append(row)
                hooks.append((target, node.fields, fi, ti, hookdata, {}))
                
    resultfields = fields[:]
    for target, fields, fi, ti, hookdata, map in hooks:
        for i, field in enumerate(fields):
            if i <> ti:
                map[i] = len(resultfields)
                resultfields.append(field)

    resultdata = []
    for row in data:
        rows = [list(row) + [None] * (len(resultfields) - len(row))]
        for target, fields, fi, ti, hookdata, map in hooks:
            # lookup match key, matching is always on original row
            newrows = []
            hookrows = hookdata[row[fi]]
            for oldrow in rows:
                for hookrow in hookrows:
                    newrow = oldrow[:]
                    for i,j in map.items():
                        newrow[j] = hookrow[i]
                    newrows.append(newrow)
            rows = newrows

        resultdata += rows
    return Node(resultfields, resultdata)

                
        
def getAllNeighbours(state, edges):
        nodes = set()
        for edge in edges: nodes.add(edge.a); nodes.add(edge.b)
        for edge2 in state.edges:
            if nodes & set([edge2.a, edge2.b]):
                if edge2 not in edges:
                    yield edge2

def getFilters(db, edges):
    valuefilters = collections.defaultdict(set)
    for e in edges:
        for field, node in ((e.mapping.a, e.a), (e.mapping.b, e.b)):
            table = e.mapping.getTable()
            if node.data:
                i = node.fields.index(field)
                valuefilters[field.getColumn(table)] |= set(row[i] for row in node.data)
            elif node.filter:
                yield node.filter.getSQL(field.getColumn(table))
    for col, values in valuefilters.iteritems():
        if all(type(v) == int for v in values):
            yield toolkit.intselectionSQL(col, values)
        else:
            yield "%s in (%s)" % (col, ",".join(map(toolkit.quotesql, values)))
        
                    
def getDatabaseOperations(state):
    usededges = set()
    for edge in state.edges:
        if (edge not in usededges) and isinstance(edge.mapping, DatabaseMapping) and (edge.a.data or edge.b.data):
            edges = set([edge])
            changed = True
            while changed:
                changed = False
                for edge2 in getAllNeighbours(state, edges):
                    if isinstance(edge2.mapping, DatabaseMapping):
                        edges.add(edge2)
                        changed = True

            usededges |= edges
            yield DatabaseOperation(edges)

            
        
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
        return max(u1, u2)
    def apply(self, state):
        """
        Method "apply" performs the actual combine action. It calls
        the combine function to map the data, and calls the removeEdge
        method of the state to update the state.
        """
        toolkit.ticker.warn("Applying map %s" % str(self))
        newnode = combine(self.edge)
        state.collapse([self.edge], newnode)
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
        return map(ReduceEdgeOperation, state.edges) + list(getDatabaseOperations(state))
       
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
