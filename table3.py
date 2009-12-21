"""
Interface and base implmentations for a generic table type

Interface Table:
  getColumns(): returns a sequence of objects that represent columns
  getRows():    returns a sequence of objects that represent rows
  getValue(row, column): returns an object representing a value given
                         two objects from getRows()/getColumns()

see tableoutput.py for useful methods for rendering tables in different ways
"""

import toolkit, types
from toolkit import isnull
from oset import OrderedSet
def trivialCellFunc(row, col): return "%s/%s" % (row, col)

class Table(object):
    def __init__(self, columns=None, rows = None, cellfunc = trivialCellFunc):
        """
        columns and rows can be given or omitted if getColumns/getRows is overridden (default [])
        cellfunc can be given as (row,col)->value, or omitted if gteValue is overridden (default: trivialcellfunc)
        """
        self.columns    = isnull(columns, []) 
        self.rows       = isnull(rows, [])
        self.cellfunc   = cellfunc            
    def getValue(self, row, column):
        return self.cellfunc(row, column)
    def getRows(self):
        return self.rows
    def getColumns(self):
        return self.columns

class ObjectColumn(object):
    def __init__(self, cellfunc):
        self.cell = cellfunc
    def getCell(self, row):
        return self.cellfunc(row)
    
class ObjectTable(Table):
    """
    Convenience subclass of Table that assumes the rows contain
    a domain object and the columns are properties of those objects
    The colunms should be ObjectColunms or some other object
    that has a getCell(row) -> value function
    """
    def __init__(self, rows = None, columns = None):
        self.rows = rows or []
        self.columns = columns or []
        self.cellfunc = lambda row, col : col.getCell(row)
    def addColumn(self, col):
        if type(col) == types.FunctionType:
            col = ObjectColumn(col)
        self.columns.append(col)
        
class DictTable(Table):
    """
    Convenience subclass of Table that creates a dict to hold the cell values,
    and adds column and row objects as needed
    """
    def __init__(self, default=None):
        Table.__init__(self, OrderedSet(), OrderedSet(),
                       lambda row, col: self.data.get((row, col), default))
        self.data = {}
    def addValue(self,row, col, value):
        self.data[row, col] = value
        self.columns.add(col)
        self.rows.add(row)
DataTable = DictTable

class ListTable(Table):
    """
    Convenience subclass of Table that is based on a list-of-lists
    such as output by dbapi::cursor.fetchall()
    if colnames is not given, toolkit.head(data) is used to determine #columns, so this will
       probably cause an undesired result for generators
    """
    def __init__(self, data, colnames = None):
        Table.__init__(self, rows=data, cellfunc = lambda row, col: row[col.id])
        if data: 
            if not colnames: colnames = range(len(toolkit.head(data)))
            self.columns = [toolkit.IDLabel(i, colname) for (i, colname) in enumerate(colnames)]
        else:
            self.columns = []


class SortedTable(Table):
    """
    Encapsulated another table object and "jit"-sorts rows as needed
    sort can be a columns, a (column, bool) pair, or a list of columns or pairs
    addsortindicator only works if columns are IDLabels
    """
    def __init__(self, table, sort):
        Table.__init__(self, cellfunc = table.getValue)
        self.table = table
        self.sort = []
        if not toolkit.isSequence(sort, excludeStrings=True) or (len(sort) == 2 and type(sort[1]) == bool):
            sort = [sort]
        for col in sort:
            if toolkit.isSequence(col): self.sort.append((col[0], col[1]))
            else: self.sort.append((col, True))
    def getColumns(self):
        """
        addindicator only works if columns are IDLabels
        """
        return self.table.getColumns()
    def cmp(self, a, b):
        for col, asc in self.sort:
            ab = [self.getValue(x, col) for x in (a,b)]
            return cmp(*ab) * (1 if asc else -1)
        return 0
    def getRows(self):
        return sorted(self.table.getRows(), cmp=self.cmp)
