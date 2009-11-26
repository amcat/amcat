def aggregate(table, selectcolumns, aggregatecolumns):
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
        self.som+=value
    def final(self):
        return self.som

class AggregateColumn(object):
    def running(self, row, table):
        abstract
    def final(self):
        abstract
        return None

class SimpleAggregateColumn(AggregateColumn):
    def __init__(self, column, aggregateFunction):
        self.column = colunm
        self.aggregateFunction = aggregateFunction
    def running(self, row):
        value = table.getValue(row, self.column)
        self.aggregateFunction.running(value)
    def final(self):
        return self.aggregateFunction.final()
        
