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


import csv
import zipfile
import io
import os

from django.template import Context, Template
from openpyxl import Workbook
import re
import datetime

from openpyxl.writer.excel import ExcelWriter

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# Used in _get_value()
INT_RE = re.compile('^[0-9]+$')
FLOAT_RE = re.compile('^(\+|-)?[0-9]*\.[0-9]+$')
DATE_RE = re.compile(r'^(\d{4})-(\d{2})-(\d{2}) (\d{2})-(\d{2})-(\d{2})$')


class TableExporter:
    """
    General export class for tables
    Subclasses or instantiators should provide either a to_stream or a to_bytes method
    """

    def __init__(self, to_stream=None, to_bytes=None, name=None):
        if to_stream is not None: self.to_stream = to_stream
        if to_bytes is not None: self.to_bytes = to_bytes
        if name:
            self._name = name

    @property
    def name(self):
        return getattr(self, '_name', None) or self.__class__.__name__

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
        # FIXME: We're ignoring encoding parameter here, because it doesn't make sense as
        # FIXME: writerow() only takes strings (not bytes).
        csvwriter = csv.writer(stream, dialect=self.dialect)

        cols = list(table.get_columns())
        csvwriter.writerow([col for col in cols])
        for row in table.get_rows():
            csvwriter.writerow([table.get_value(row, col) for col in cols])


class CSV_semicolon(CSV):
    name = "CSV (semicolon)"

    class dialect(csv.excel):
        delimiter = ";"


def _convert_value(value):
    if not isinstance(value, str):
        return value

    if INT_RE.match(value) is not None:
        return int(value)

    if FLOAT_RE.match(value) is not None:
        return float(value)

    m = DATE_RE.match(value)
    if m:
        return datetime.datetime(*map(int, m.groups()))

    return value


def _get_values(table, row):

    for column in table.get_columns():
        yield _convert_value(table.get_value(row, column))


class XLSX(TableExporter):
    extension = "xlsx"

    def to_bytes(self, table, **kargs):
        wb = Workbook(optimized_write=True)
        ws = wb.create_sheet()

        # Determine columns. We may need an extra (first) column which 'names' the row
        columns = list(map(str, list(table.get_columns())))
        ws.append(columns)

        # Write rows to worksheet
        for row in table.get_rows():
            ws.append(tuple(_get_values(table, row)))
        writer = ExcelWriter(wb)

        # Need to do a little bit more work here, since the openpyxl library only
        # supports writing to a filename, while we need a buffer here..
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            writer.write_data(zf)
        return buffer.getvalue()


HTML_FILENAME = os.path.join(os.path.dirname(__file__), "templates/articles.html")

template = None
def get_template():
    global template
    if template is None:
        template = Template(open(HTML_FILENAME).read())
    return template


class HTML(TableExporter):
    extension = "html"

    def to_bytes(self, table, encoding):
        context = Context({
            "articles": table.get_rows(), "encoding": encoding,
            "non_meta": {"text", "title", "byline"}
        })
        return get_template().render(context).encode(encoding)


class SPSS(TableExporter):
    extension = 'spss'

    def to_bytes(self, table, **kargs):
        from . import table2spss
        filename = table2spss.table2sav(table)
        contents = open(filename, 'rb').read()
        os.unlink(filename)
        return contents


EXPORTERS = {
    'csv': CSV(),
    'csv2': CSV_semicolon(),
    'xlsx': XLSX(),
    'spss': SPSS(),
    'html': HTML()
}
