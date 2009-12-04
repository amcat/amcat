import toolkit, types
from toolkit import isnull

def trivialCellFunc(row, col): return "%s/%s" % (row, col)

class Table(object):
    def __init__(self, columns=None, rows = None, cellfunc = trivialCellFunc):
        self.columns    = isnull(columns, []) # data objects representing columns
        self.rows       = isnull(rows, [])    # data objects representing row
        self.cellfunc   = cellfunc            # function: row, col -> value
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
        
class DataTable(Table):
    """
    Convenience subclass of Table that creates a dict to hold the cell values,
    and adds column and row objects as needed
    """
    def __init__(self, default=None):
        Table.__init__(self)
        self.data = {}
        self.default = default
        self.columns = SimpleOrderedSet()
        self.rows = SimpleOrderedSet()
        self.cellfunc =  lambda row, col: self.data.get((row, col), default)
    def addValue(self,row, col, value):
        self.data[row, col] = value
        self.columns.add(col)
        self.rows.add(row)


class SimpleOrderedSet(list):
    def __init__(self):
        list.__init__(self)
        self.set = set()
    def add(self, object):
        if object in self.set: return
        self.set.add(object)
        self.append(object)

