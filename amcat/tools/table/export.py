# ##########################################################################
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

# exportfunction(table, outfile

from cStringIO import StringIO
import csv
import zipfile
import io
import os

from django.template import Context, Template
from openpyxl import Workbook
from openpyxl.writer.dump_worksheet import ExcelDumpWriter
import re

# Used in _get_value()
FLOAT_RE = re.compile('^(\+|-)?[0-9]*\.[0-9]+$')


class TableExporter():
    """
    General export class for tables
    Subclasses or instantiators should provide either a to_stream or a to_bytes method
    """

    def __init__(self, to_stream=None, to_bytes=None, name=None):
        if to_stream is not None: self.to_stream = to_stream
        if to_bytes is not None: self.to_bytes = to_bytes
        if name: self.name = name

    @property
    def name(self):
        # overwritten by self.name
        return self.__class__.__name__

    def export(self, table, stream=None, encoding="utf-8", **kargs):
        """
        Export the table to the given stream. 
        @return: str if stream is None, otherwise undefined
        """
        if hasattr(self, "to_stream"):
            if stream is None:
                stream = StringIO()
            self.to_stream(table, stream, encoding=encoding, **kargs)
            try:
                return stream.getvalue()
            except AttributeError:
                return
        else:
            bytes = self.to_bytes(table, encoding=encoding, **kargs)
            if stream is not None:
                stream.write(bytes)
                return
            else:
                return bytes


class CSV(TableExporter):
    extension = "csv"
    dialect = csv.excel

    def to_stream(self, table, stream, encoding):
        def encode(val):
            if val is None: return val
            return unicode(val).encode(encoding)

        csvwriter = csv.writer(stream, dialect=self.dialect)

        cols = list(table.getColumns())
        csvwriter.writerow([encode(col) for col in cols])
        for row in table.getRows():
            csvwriter.writerow([encode(table.getValue(row, col)) for col in cols])


class CSV_semicolon(CSV):
    name = "CSV (semicolon)"

    class dialect(csv.excel):
        delimiter = ";"


def _convert_value(value):
    if not isinstance(value, basestring):
        return value

    if FLOAT_RE.match(value) is not None:
        return float(value)

    return value


def _get_values(table, row):
    # TODO: Remove hacks by accessing type info?
    if table.rowNamesRequired:
        yield unicode(row)

    for column in table.getColumns():
        yield _convert_value(table.getValue(row, column))


class XLSX(TableExporter):
    extension = "xlsx"

    def to_bytes(self, table, **kargs):
        wb = Workbook(optimized_write=True)
        ws = wb.create_sheet()

        # Determine columns. We may need an extra (first) column which 'names' the row
        columns = list(map(unicode, list(table.getColumns())))
        if table.rowNamesRequired:
            columns.insert(0, u"")
        ws.append(columns)

        # Write rows to worksheet
        for row in table.getRows():
            ws.append(tuple(_get_values(table, row)))
        writer = ExcelDumpWriter(wb)

        # Need to do a little bit more work here, since the openpyxl library only
        # supports writing to a filename, while we need a buffer here..
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            writer.write_data(zf)
        return buffer.getvalue()


HTML_FILENAME = os.path.join(os.path.dirname(__file__), "templates/articles.html")


class HTML(TableExporter):
    extension = "html"
    template = Template(open(HTML_FILENAME).read())

    def to_bytes(self, table, encoding):
        context = Context({
            "articles": table.getRows(), "encoding": encoding,
            "non_meta": {"text", "headline", "byline"}
        })
        return self.template.render(context).encode(encoding)


class SPSS(TableExporter):
    extension = 'spss'

    def to_bytes(self, table, **kargs):
        from . import table2spss

        filename = table2spss.table2sav(table)
        return open(filename, 'rb').read()


EXPORTERS = {
    'csv': CSV(),
    'csv2': CSV_semicolon(),
    'xlsx': XLSX(),
    'spss': SPSS(),
    'html': HTML()
}
