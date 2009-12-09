import table3, associations

""" 
Uitdagingen:
1) aggregateTable -> table3.Table object teruggeven
2) sourceinterface.getTable(..) implementeren
3) association als aggregatecolumn
"""

def aggregate(table, selectcolumns, aggregatecolumns):
    dict = {}
    for row in table.getRows():
        key = tuple(table.getValue(row, col) for col in selectcolumns)
        if not dict.has_key(key):
            vals = tuple(a.getAggregateFunction() for a in aggregatecolumns)
            dict[key] = vals
        for col, func in zip(aggregatecolumns, dict[key]):
            col.running(table, row, func)            
    for key,funcs in dict.iteritems():
        values = tuple(col.final(func) for (col, func) in zip(aggregatecolumns, funcs))
        yield key, values

def getAggregateTable(table, selectcolumns, aggregatecolumns):
    values = aggregate(table, selectcolumns, aggregatecolumns)
    aggDict = dict(values)
    aggTable = table3.Table(aggDict, [tuple((x, y)) for x, y in aggDict.iteritems()])
    return aggTable

class AggregateFunction(object):
    def running(self, value):
        abstract
    def final(self):
        abstract
        return None

class Sum(AggregateFunction):
    def __init__(self):
        self.som = 0
    def running(self, value):
        if value is not None:
            self.som+=value
    def final(self):
        return self.som
 
class Count(AggregateFunction):
    def __init__(self):
        self.n = 0
    def running(self, value):
        if value is not None:
            self.n += 1
    def final(self):
        return self.n   
    
class Average(AggregateFunction):
    def __init__(self):
        self.count = 0
        self.total = 0
    def running(self, value):
        if value is not None:
            self.count += 1
            self.total += value
    def final(self):
        return self.total / float(self.count)
            
class AggregateColumn(object):
    def __init__(self, factory=None):
        self.factory = factory
    def getAggregateFunction(self):
        return self.factory()
    def running(self, table, row, function):
        function.running(self.getValue(table, row))
    def getValue(self, table, row):
        abstract
    def final(self, function):
        return function.final()
    def getConcepts(self):
	return []

class SimpleAggregateColumn(AggregateColumn):
    def __init__(self, column, aggregateFactory):
        AggregateColumn.__init__(self, aggregateFactory)
        self.column = column
    def getValue(self, table, row):
        return table.getValue(row, self.column)
    def getConcepts(self):
	return [self.column]
    
class ListTable(object):
    def __init__(self, lst):
        self.lst = lst
        self.ncols = len(lst[0]) if lst else 0
    def getRows(self):
        return self.lst
    def getColumns(self):
        return range(self.ncols)
    def getValue(self,row,column):
        return row[column]

if __name__ == '__main__':
    print "Test aggregate()"
    #table = ListTable([[1,2,3,4,5],[3,4,8,9,10],[1,2,2213,53654,234234]])
    #a = sumaggregate(table, [0,1],[3,4], Average)
    
    table = ListTable([[1,1,2],[1,1,5],[1,2,None], [1,2,8], [2,1,4]])
    
    #avg = SimpleAggregateColumn([1], Average)
    a = aggregate(table, [0,1],[SimpleAggregateColumn(2, Sum), SimpleAggregateColumn(2, Count), SimpleAggregateColumn(2, Average)])
    at = getAggregateTable(table,[0,1],[SimpleAggregateColumn(2, Sum), SimpleAggregateColumn(2, Count), SimpleAggregateColumn(2, Average)])
    print at.getRows()
    
    #print dict(a)
    #print a
    for k, v in sorted(a):
        print k, v
        
    print "\nTest simpleaggregatecolumn"
    s = SimpleAggregateColumn(0, Sum)
    f = s.getAggregateFunction()
    for row in table.getRows():
        s.running(table, row, f)
    print s.final(f)
    
    
