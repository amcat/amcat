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

# exportfunction(table, outfile

from cStringIO import StringIO
import csv, zipfile

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

class CSV(TableExporter):
    extension="csv"
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


class XLSX(TableExporter):
    extension = "xlsx"
    def to_bytes(self, table, **kargs):
        # Import openpyxl "lazy" to prevent global dependency
        def val(x):
            return x if x is None else unicode(x)
        
        from openpyxl.workbook import Workbook
        from openpyxl.writer.dump_worksheet import ExcelDumpWriter

        wb = Workbook(optimized_write = True)
        ws = wb.create_sheet()


        cols =  list(table.getColumns())
        ws.append([val(col) for col in  cols])
        
        for row in table.getRows():
            ws.append([val(table.getValue(row, col)) for col in cols])

        writer = ExcelDumpWriter(wb)
        # need to do a little bit more work here, since the openpyxl library only supports writing to a filename, while we need a buffer here..
        # (and we can't stream directly as zipfile needs a seekable buffer)
        stream = StringIO()
        zf = zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED)
        writer.write_data(zf)
        zf.close()
        return stream.getvalue()

EXPORTERS = {'csv' : CSV(),
             'csv2' : CSV_semicolon(),
             'xlsx' : XLSX()
             }
