import toolkit
import operation
from tabulatorstate import State
import mst2

class Tabulator(object):
    """
    Class Tabulator creates a tabular data structure from a datamodel,
    a select clause, and a filter clause. 
    """
    def __init__(self, datamodel, select, filters, operationfactory=None):
        """
        Datamodel should be a datasource.DataModel instance containing the data to process
        Select is the list of concepts we want as output
        Filters is a mapping of concept:values to limit the data
        """
        self.datamodel = datamodel
        self.operationsFactory = operationfactory or operation.OperationsFactory()
        self.select = select
        self.filters = filters

    def getRoute(self, concepts):
        return mst2.getSolution(self.datamodel.getMappings(), concepts)
                 
    def getData(self):
        """
        Returns a list of lists representing the solution
        """
        select = set(self.select)
        select |= set(self.filters.keys())
        route = self.getRoute(select)
        print "Got Route"
        state = State(self, route, self.filters)
        while state.solution is None:
            best = toolkit.choose(self.operationsFactory.getOperations(state),
                                  lambda op: op.getUtility(state))
            state = best.apply(state)
        return self._getColumns(state.solution)
    def _getColumns(self, node):
        if not node.data or node.fields == self.select: return node.data
        indices = map(node.fields.index, self.select)
        result = []
        for row in node.data:
            result.append(tuple(map(lambda i: row[i], indices)))
        return result
        
    def clean(self, state, node):
        """
        Postprocess a newly created node for optimization
        Currently, removes unnecessary columns
        """
        # we keep columns that (1) are in select or (2) are contained in mappings
        keep = set(self.select)
        for edge in state.edges:
            if edge.a == node:
                keep.add(edge.mapping.a)
            if edge.b == node:
                keep.add(edge.mapping.b)
        dellist = [i for (i, field) in enumerate(node.fields) if field not in keep]
        dellist.sort(reverse=True)
        for row in node.data:                                    
            for i in dellist:
                del row[i]
        for i in dellist:
            del node.fields[i]
        return node

def tabulate(datamodel, select, filters):
    return Tabulator(datamodel, select, filters).getData()
    
