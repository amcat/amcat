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
  get_columns(): returns a sequence of objects that represent columns
  get_rows():    returns a sequence of objects that represent rows
  get_value(row, column): returns an object representing a value given
                         two objects from get_rows()/get_columns()

see tableoutput.py for useful methods for rendering tables in different ways
"""

import re
import logging

from amcat.contrib.oset import OrderedSet
from amcat.tools import toolkit, idlabel
from amcat.tools.table import tableoutput
from amcat.tools.table.export import EXPORTERS
from collections import namedtuple

log = logging.getLogger(__name__)


class Table(object):
    """Generic interface on rectangular tables.

    Supports read access using get_rows/get_columns/get_value and
    using index access to and iteration over the 'Named' rows
    e.g. print(row[1].colA); for row in table:(print(row.colB))

    This is primarily meant for subclassing, but a base implementation
    works by giving columns and rows as sequences and a function that
    maps column and row to a value.
    """

    def __init__(self, columns=None, rows=None, cellfunc="{}/{}".format,
                 columnTypes=None, **kargs):
        """
        @param columns: a sequence of columns, or None if get_columns is overridden
        @param rows:a sequence of rows, or None if get_rows is overridden
        @param cellfunc: a function taking a row and column argument, or None
                         if get_value is overridden.
        """
        self.columns = columns or []
        self.rows = rows or []
        self.cellfunc = cellfunc
        self.columnTypes = dict(zip(self.get_columns(), columnTypes or []))

    def get_value(self, row, column):
        """Get the value corresponding to this row and column"""
        return self.cellfunc(row, column)

    def get_rows(self):
        """Get a sequence of objects representing the rows"""
        return self.rows

    def get_columns(self):
        """Get a sequence of objects representing the columns"""
        return self.columns

    def get_column_type(self, column):
        if column in self.columnTypes:
            return self.columnTypes[column]
        return getattr(column, "fieldtype", None)

    def __getitem__(self, index):
        """Get the n-th column"""
        return list(self.get_rows())[index]

    def output(self, **kargs):
        """Output the table; see tableoutput.table2unicode for options"""
        return tableoutput.table2unicode(self, **kargs)

    def to_csv(self, **kargs):
        return self.export(format='csv', **kargs)

    def export(self, format, **kargs):
        return EXPORTERS[format].export(self, **kargs)

    def to_list(self, tuple_name="row", row_names=False):
        """Return the data in the table as a sequence of named tuples

        @param tuple_name: the name for the named tuples, or None to get simple tuples
        """
        cols = self.get_columns()
        if tuple_name:
            colnames = [re.sub(r"\W", "", str(col)) for col in cols]
            t = namedtuple(tuple_name, colnames, rename=True)
            factory = lambda values: t(*values)
        else:
            factory = tuple
        for row in self.get_rows():
            vals = [self.get_value(row, col) for col in cols]
            if row_names: vals.insert(0, row)
            yield factory(vals)


class ObjectTable(Table):
    """
    Convenience subclass of Table that assumes the rows contain
    a domain object and the columns are properties of those objects
    The colunms should be ObjectColunms or some other object
    that has a get_cell(row) -> value function
    """

    def __init__(self, rows=None, columns=None):
        Table.__init__(self, columns=[], rows=rows or [])
        if columns:
            for column in columns:
                self.add_column(column)

    def add_column(self, col, label=None, index=None, **kargs):
        """Add column to Table3 object
        
        @type col: ObjectColumn, string, or (lambda-)function
        @param col: Column you want to add to this table. If it is
        a function, it will be called with an object every time
        a cell is created. The returned data will be used to fill it. If
        if is a string, use it as an attribute getter 
        
        @type label: str
        @param label: String for user-friendly column-identification.
        If not provided, the __name__ attribute of `col` will be used.
        
        @type return: NoneType 
        """
        if hasattr(col, '__call__'):  # function
            if label is None:
                label = col.__name__

            if label == '<lambda>':
                label = ''

            col = ObjectColumn(label, col, **kargs)
        elif isinstance(col, str):
            col = AttributeColumn(col, label, **kargs)
        if index is not None:
            self.columns.insert(index, col)
        else:
            self.columns.append(col)
        return col

    def get_value(self, row, column):
        """Get the column-value for the given row object"""
        return column.get_cell(row)


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

    def get_cell(self, row):
        """Calculate/get the value of this column for the given row object
        Default implementation calls self.rowfunc
        """
        try:
            return self.cellfunc(row)
        except:
            log.error("Exception on getting column %r on row %r" % (self.label, row))
            raise

    def __bytes__(self):
        return self.label.encode('utf-8')

    def __str__(self):
        return str(self.label)


class AttributeColumn(ObjectColumn):
    """An ObjectColumn subclass that works as an attribute getter"""

    def __init__(self, attribute, label=None, **kargs):
        if not label: label = attribute
        super(AttributeColumn, self).__init__(label, **kargs)
        self.attribute = attribute

    def get_cell(self, row):
        """Returns the right attribute of the given row object"""
        return getattr(row, self.attribute)


class ListTable(Table):
    """
    Convenience subclass of Table that is based on a list-of-lists
    such as output by dbapi::cursor.fetchall()
    if colnames is not given, len(rows[0]) is used to determine #columns, causing an error
       if the data is not subscriptable
    """

    def __init__(self, data=None, colnames=None, **kwargs):
        self.colnames = colnames
        super(ListTable, self).__init__(rows=data or [], **kwargs)

    def get_columns(self):
        if not (self.colnames or self.rows): return []
        colnames = self.colnames or range(len(toolkit.head(self.rows)))
        return [idlabel.IDLabel(i, colname) for (i, colname) in enumerate(colnames)]

    def addRow(self, *row):
        """Append a row of values to the internal list-of-lists"""
        self.rows.append(row)

    def get_value(self, row, col):
        if col.id >= len(row): return None
        return row[col.id]


class WrappedTable(Table):
    """Base class for encapsulating another table to provide a different 'view' on it"""

    def __init__(self, table, *args, **kargs):
        super(WrappedTable, self).__init__(*args, **kargs)
        self.table = table
        self._kargs = kargs

    def get_columns(self):
        return self.columns if self.columns else self.table.get_columns()

    def get_rows(self):
        return self.rows if self.rows else self.table.get_rows()

    def get_value(self, row, col):
        val = self.table.get_value(row, col)
        if 'cellfunc' in self._kargs:
            val = self._kargs['cellfunc'](val)
        return val


class SortedTable(WrappedTable):
    """Wrapped table where get_rows() returns an ordered table, according to a user
    specified key function."""
    def __init__(self, table, key, reverse=False):
        super(SortedTable, self).__init__(table)
        self.key = key
        self.reverse = reverse

    def get_rows(self):
        return sorted(self.table.get_rows(), key=self.key, reverse=self.reverse)

