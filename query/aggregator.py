###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

class AggregateFunction(object):
    """abstract class for creating an aggregate function; update the total by using running; final returns the final value """
    def running(self, value):
        abstract
    def final(self):
        abstract
        return None

class Sum(AggregateFunction):
    """Aggregate function to sum the values in a column """
    def __init__(self):
        self.som = 0
    def running(self, value):
        if value is not None:
            self.som+=value
    def final(self):
        return self.som
 
class Count(AggregateFunction):
    """Aggregate function to count the elements in a column """
    def __init__(self):
        self.n = 0
    def running(self, value):
        if value is not None:
            self.n += 1
    def final(self):
        return self.n   
    
class Average(AggregateFunction):
    """Aggregate function to calculate the average of the values in a column """
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
    """
    abstract class for aggregating a column 
    factory := the aggregate function
    """
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
    """ 
    column := [concepts on which to perform the aggregatefunction]
    aggregateFactory := aggregate functions
    """
    def __init__(self, column, aggregateFactory):
        AggregateColumn.__init__(self, aggregateFactory)
        self.column = column
    def getValue(self, table, row):
        return table.getValue(row, self.column)
    def getConcepts(self):
	return [self.column]
    
class ListTable(object):
    """ 
    lst := a list of lists (matrix)
    Returns a Table object with accessors to the data 
    """
    def __init__(self, lst):
        self.lst = lst
        self.ncols = len(lst[0]) if lst else 0
    def getRows(self):
        return self.lst
    def getColumns(self):
        return range(self.ncols)
    def getValue(self,row,column):
        return row[column]

