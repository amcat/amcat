def aggregate(table, selectcolumns, aggregatecolumns):
    dict = {}
    set_keys = set()
    for row in table.getRows():
        t = tuple(selectcolumns)
        set_keys.add(t)
        if set_keys.__contains__() 

    aggr = SimpleAggregateColumn(aggregatecolumn)
    sum = Sum(aggr)
    
    return Table()


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

class AggregateColumn(object):
    def running(self, row, table):
        abstract
    def final(self):
        abstract
        return None

class SimpleAggregateColumn(AggregateColumn):
    def __init__(self, columns, aggregateFactory):
        self.columns = columns
        self.aggregateFactory = aggregateFactory
    def getAggregate(self):
        return self.aggregateFactory()
    def getValue(self, table, row):
        return [table.getValue(row, column) for column in self.columns]
        
if __name__ == '__main__':
    s = SimpleAggregateColumn([], Count)
    a = s.getAggregate()
    print s.getValue(None, None)
    a.running(s.getValue(None, None))
    print a.final()
    
    