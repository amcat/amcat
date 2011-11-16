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

"""
Interface and base implmentations for a generic table type

Interface Table:
  getColumns(): returns a sequence of objects that represent columns
  getRows():    returns a sequence of objects that represent rows
  getValue(row, column): returns an object representing a value given
                         two objects from getRows()/getColumns()

see tableoutput.py for useful methods for rendering tables in different ways
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools import toolkit, idlabel
from amcat.tools.toolkit import isnull

import types
from amcat.contrib.oset import OrderedSet

import logging; log = logging.getLogger(__name__)


def trivialCellFunc(row, col):
    """'Default' cell function that returns a string representation row/col"""
    return "%s/%s" % (row, col)

class Table(object):
    """Generic interface on rectangular tables.

    Supports read access using getRows/getColumns/getValue and
    using index access to and iteration over the 'Named' rows
    e.g. print row[1].colA; for row in table: print(row.colB)

    This is primarily meant for subclassing, but a base implementation
    works by giving columns and rows as sequences and a function that
    maps column and row to a value.
    """
    def __init__(self, columns=None, rows = None, cellfunc = trivialCellFunc,
                 rowNamesRequired = False):
        """
        @param columns: a sequence of columns, or None if getColumns is overridden
        @param rows:a sequence of rows, or None if getRows is overridden
        @param cellfunc: a function taking a row and column argument, or None
                         if getValue is overridden.
        @param rowNamesRequired: a hint to output functions that rownames should be printed
        """
        self.columns    = isnull(columns, []) 
        self.rows       = isnull(rows, [])
        self.cellfunc   = cellfunc
        self.rowNamesRequired = rowNamesRequired

    # Basic table interface
    def getValue(self, row, column):
        """Get the value corresponding to this row and column"""
        result =  self.cellfunc(row, column)
        return result
    def getRows(self):
        """Get a sequence of objects representing the rows"""
        return self.rows
    def getColumns(self):
        """Get a sequence of objects representing the columns"""
        return self.columns

    # Convenience access using iteration / index and NamedRows
    def getNamedRows(self):
        """Get a sequence of NamedRow objects that can be used to access the values"""
        for r in self.getRows():
            yield NamedRow(self, r)
    def getNamedRow(self, rowname):
        """Get a NamedRow object for the given row(name)"""
        for r in self.getRows():
            if r == rowname:
                return NamedRow(self, r)
        return None       
    def __iter__(self):
        return iter(self.getNamedRows())
    def __getitem__(self, index):
        """Get the n-th column"""
        return list(self.getRows())[index]
    

class NamedRow(object):
    """Interface for a row in a table that supports attribute and index access"""
    def __init__(self, table, row):
        self.table = table
        self.row = row
    def get(self, column):
        """Get the specified column on this row?"""
        for col in self.table.getColumns():
            if str(col) == column:
                return self.table.getValue(self.row, col)
    def __getattr__(self, attr):
        """If attr is the str(col) for any column, return that column"""
        if attr != 'table':
            for col in self.table.getColumns():
                if str(col) == attr:
                    return self.table.getValue(self.row, col)
        return super(NamedRow, self).__getattribute__(attr)
    def __getitem__(self, index):
        """Get the n-th column"""
        col = list(self.table.getColumns())[index]
        return self.table.getValue(self.row, col)
    def __iter__(self):
        """Iterate over the columns"""
        for c in self.table.getColumns():
            yield self.table.getValue( self.row, c)

    
# Why are these here?
OBJECTCOLUMN_PROPERTIES = ('fieldname', 'fieldtype', 'label',
                           'visible', 'editable', 'url')

class ObjectTable(Table):
    """
    Convenience subclass of Table that assumes the rows contain
    a domain object and the columns are properties of those objects
    The colunms should be ObjectColunms or some other object
    that has a getCell(row) -> value function
    """
    def __init__(self, rows = None, columns = None):
        Table.__init__(self, columns=columns or [], rows = rows or [])
    def addColumn(self, col, label=None, **kargs):
        """Add column to Table3 object
        
        @type col: ObjectColumn, string, or (lambda-)function
        @param col: Column you want to add to this table. If it is
        a function, it will be called with an object every time
        a cell is created. The returned data will be used to fill it. If
        if is a string, use it as an attribute getter 
        
        @type label: str or unicode
        @param label: String for user-friendly column-identification.
        If not provided, the __name__ attribute of `col` will be used.
        
        @type return: NoneType 
        """
        if hasattr(col, '__call__'): # function
            if label is None: label = col.__name__
            if label == '<lambda>': label = ''
            
            col = ObjectColumn(label, col, **kargs)
        elif type(col) in (str, unicode):
            col = AttributeColumn(col, label, **kargs)
        self.columns.append(col)
    def getValue(self, row, column):
        """Get the column-value for the given row object"""
        return column.getCell(row)
        
class ObjectColumn(object):
    """An ObjectColumn is a column on an ObjectTable that gets a value
    on an object by calling the cellfunc(obj)"""
    def __init__(self, label, cellfunc=None, fieldname=None, fieldtype=None, 
                 visible=True, editable=True, url=None):
        self.label = label
        self.cellfunc = cellfunc
        self.fieldname = fieldname or label
        self.fieldtype = fieldtype
        self.visible = visible
        self.editable = editable
        self.url = url
    def getCell(self, row):
        """Calculate/get the value of this column for the given row object
        Default implementation calls self.rowfunc
        """
        return self.cellfunc(row)
    def __str__(self):
        return self.label

class AttributeColumn(ObjectColumn):
    """An ObjectColumn subclass that works as an attribute getter"""
    def __init__(self, attribute, label=None, **kargs):
        if not label: label = attribute
        super(AttributeColumn, self).__init__(label, **kargs)
        self.attribute = attribute
    def getCell(self, row):
        """Returns the right attribute of the given row object"""  
        return getattr(row, self.attribute)
        
class FormTable(ObjectTable):
    """Wrapper around ObjectTable. Get its default columns from a Form
    object."""
    
    def __init__(self, form, objects, rowurl=None, idcolumn=None):
        """
        @type form: Django Form (django.forms.Form)
        
        @type idcolumn: int or tuple
        @param idcolumn: Which column(s) are unique
        
        @type rowurl: formattable string
        @param rowurl: keywords will be replaced with value of
        column-cell.
        @example rowurl: "/user/{id}/"
        
        @type objects: A cachable object"""
        super(FormTable, self).__init__(objects)
        
        self.form = form if hasattr(form, 'fields') else form()
        self.idcolumn = toolkit.idlist(idcolumn or self.form.Meta.model.__idcolumn__)
        self.rowurl = rowurl
        
        for fname in self.form.Meta.table:
            self._addColumn(fname, self.form.fields[fname])
        
        columns = [c.fieldname for c in self.columns]
        for c in self.idcolumn:
            if c not in columns:
                self._addColumn(c, self.form.fields[c], visible=False)
        
                
    def _addColumn(self, name, field, visible=True):
        label = field.label or name.capitalize()
        col = self._createCellfunc(field, name)
        fieldtype = field.__class__.__name__
        
        url = None
        if toolkit.hasattrv2(self.form, 'Meta.links'):
            self.form.Meta.links.get(name, None)
        
        self.addColumn(col, label,
                       fieldname=name,
                       fieldtype=fieldtype,
                       url=url,
                       visible=visible)
            
    def _createCellfunc(self, field, name):
        """Create a lambda function outside __init__ avoiding scoping issues"""
        def foreign_key(x):
            # Custom function for `one to many` or `one to one` relations
            attr = getattr(x, name)
            if type(attr) == types.GeneratorType:
                # One to many relation
                return len(tuple(attr))
            # One to one
            return attr.label
        
        if hasattr(field, 'count') or hasattr(field, 'choices'):
            return foreign_key
        return lambda x:getattr(x, name)
        
        
        
class DictTable(Table):
    """
    Convenience subclass of Table that creates a dict to hold the cell values,
    and adds column and row objects as needed
    """
    def __init__(self, default=None):
        Table.__init__(self, OrderedSet(), OrderedSet(),
                       self.getValue)
        self.data = {}
        self.default = default
    def addValue(self, row, col, value):
        """Set the given value in the data dict"""
        self.data[row, col] = value
        self.columns.add(col)
        self.rows.add(row)
    def getValue(self, row, col):
        return self.data.get((row, col), self.default)
    def __getstate__(self):
        d = self.__dict__
        if d['cellfunc'] == self.getValue: del d['cellfunc']
        return d
    def __setstate__(self, d):
        if 'cellfunc' not in d: d['cellfunc'] = self.getValue
        self.__dict__ = d
    
DataTable = DictTable

class ListTable(Table):
    """
    Convenience subclass of Table that is based on a list-of-lists
    such as output by dbapi::cursor.fetchall()
    if colnames is not given, len(rows[0]) is used to determine #columns, causing an error
       if the data is not subscriptable
    """
    def __init__(self, data=None, colnames=None):
        super(ListTable, self).__init__(rows=data or [])
        self.colnames = colnames
    def getColumns(self):
        if not (self.colnames or self.rows): return []
        colnames = self.colnames or range(len(toolkit.head(self.rows)))
        return [idlabel.IDLabel(i, colname) for (i, colname) in enumerate(colnames)]
    def addRow(self, *row):
        """Append a row of values to the internal list-of-lists"""
        self.rows.append(row)
    def getValue(self, row, col):
        if col.id >= len(row): return None
        return row[col.id]

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
        if not toolkit.isSequence(sort, excludeStrings=True) or (
            len(sort) == 2 and type(sort[1]) == bool):
            sort = [sort]
        for col in sort:
            if toolkit.isSequence(col): self.sort.append((col[0], col[1]))
            else: self.sort.append((col, True))
    def getColumns(self):
        return self.table.getColumns()
    def cmp(self, a, b):
        """Compare rows a and b for use in sorting"""
        for col, asc in self.sort:
            ab = [self.getValue(x, col) for x in (a, b)]
            return cmp(*ab) * (1 if asc else -1)
        return 0
    def getRows(self):
        return sorted(self.table.getRows(), cmp=self.cmp)

class MergedTable(Table):
    """
    Encapsulates two table objects, displaying columns side-by-side
    """
    def __init__(self, *tables):
        """
        tables can be any number of Table objects
        """
        self.tables = list(tables)
        self.columnfilter = lambda t, c: True # table, column -> bool
    def getColumns(self):
        result = []
        for table in self.tables:
            result += [idlabel.IDLabel((table, c), c)
                       for c in table.getColumns()
                       if self.columnfilter(table, c)]
        return result
    def getRows(self):
        # Iterators would be good here!
        rowss = [t.getRows() for t in self.tables]
        for i in range(max(map(len, rowss))):
            row = []
            for rows in rowss:
                if len(rows) <= i: row.append(None)
                else: row.append(rows[i])
            yield row
    def getValue(self, row, col):
        table, col = col.id
        row = row[self.tables.index(table)]
        if not row: return None
        return table.getValue(row, col)

class ColumnViewTable(Table):
    def __init__(self, table, columns, uselabel=True):
        self.table = table
        self.columns = set(columns)
        self.uselabel = uselabel
    def getColumns(self):
        for col in self.table.getColumns():
            if col in self.columns or (
                self.uselabel and isinstance(col, idlabel.IDLabel) and col.label in self.columns):
                yield col
    def getRows(self):
        return self.table.getRows()
    def getValue(self, row, col):
        return self.table.getValue(row, col)

class PostProcessTable(Table):
    def __init__(self, table, valuefunc=None):
        self.table = table
        self.valuefunc = valuefunc
    def getColumns(self):
        return self.table.getColumns()
    def getRows(self):
        return self.table.getRows()
    def getValue(self, row, col):
        v = self.table.getValue(row, col)
        return self.valuefunc(self, v, row, col)
    
def getColumnByLabel(table, label):
    stringify = unicode if type(label) == unicode else str
    for c in table.getColumns():
        if stringify(c) == label: return c



                 
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

def _striplines(x):
    return "\n".join(l.strip() for l in x.split("\n")).strip()

class TestTable(amcattest.PolicyTestCase):
    def test_list_table(self):
        """Can we create a list table and output as ascii"""
        from . import tableoutput

        t = ListTable(colnames = ["a1", "a2", "a3"],
                      data = [[1,2,3],
                              [74321,8,9],
                              [4,5,"asdf"],
                              ])
        result = tableoutput.table2ascii(t)
        correct = u'''
a1    | a2 | a3    
------+----+-----
1     | 2  | 3     
74321 | 8  | 9     
4     | 5  | asdf'''
        self.assertEquals( _striplines(result), _striplines(correct.strip()))

    def test_object_table(self):
        """Does creating object tables work"""
        from . import tableoutput
        class Test(object):
            def __init__(self, a, b, c):
                self.a, self.b, self.c = a, b, c
            
        l = ObjectTable(rows=[Test(1, 2, 3), Test("bla",None, 7), Test(-1, -1, None)])
        l.addColumn(lambda x: x.a, "de a")
        l.addColumn("b")
        l.addColumn(ObjectColumn("en de C", lambda x: x.c))
        
        result = tableoutput.table2unicode(l)
        # get rid of pesky unicode
        result = result.translate(dict((a, 65+a%26) for a in range(0x2500, 0x2600)))

        correct = '''OKKKKKKEKKKKEKKKKKKKKKR
L de a K b  K en de C L
ZIIIIIIQIIIIQIIIIIIIIIC
L 1    K 2  K 3       L
L bla  K    K 7       L
L -1   K -1 K         L
UKKKKKKHKKKKHKKKKKKKKKX'''
        self.assertEquals( _striplines(result), _striplines(correct.strip()))
            
# if __name__ == '__main__':
#     import tableoutput
#     t = ListTable(colnames = ["a1", "a2", "a3"],
#                   data = [[1,2,3],
#                           [7,8,9],
#                           [4,5,6],
#                           ])


#     print(tableoutput.table2ascii(t))

#     s = SortedTable(t, getColumnByLabel(t, "a2"))
#     print(tableoutput.table2ascii(s))
    
#     t2 = ListTable(colnames = ["b1", "b2"],
#                    data = [['a','A'],
#                            ['c','C'],
#                            ['d','D'],
#                            ['b','B'],
#                            ])
    
#     print(tableoutput.table2ascii(t2))
#     m = MergedTable(t, t2)
#     m.columnfilter = lambda tab,col : col.label <> "a1"
#     print(tableoutput.table2ascii(m))

#     l = getColumnByLabel(m, "b1")
#     print(l)
#     s = SortedTable(m, getColumnByLabel(m, "b1")) 
#     print(tableoutput.table2ascii(s))

#     import article, dbtoolkit
#     a = article.Article(dbtoolkit.amcatDB(), 33308863)
#     a2 = article.Article(dbtoolkit.amcatDB(), 33308864)

#     hl = ObjectColumn("headline", lambda a: a.headline)
#     id = ObjectColumn("id", lambda a: a.id)
    
#     l = ObjectTable([a,a2], [hl, id])
#     print(tableoutput.table2ascii(l))
    
