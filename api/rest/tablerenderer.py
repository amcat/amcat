# From: https://github.com/mjumbewu/django-rest-framework-csv
# Copyright Mjumbe Wawatu Poe.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer. Redistributions in binary
# form must reproduce the above copyright notice, this list of conditions and
# the following disclaimer in the documentation and/or other materials provided
# with the distribution. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import csv

from collections import OrderedDict
from functools import partial

from rest_framework.renderers import *
from amcat.tools.table import table3
from amcat.tools.amcatr import create_dataframe, save_to_bytes, to_r

import logging


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

class TableRenderer(BaseRenderer):
    """
    Generic (abstract) renderer which flattens the table before writing.
    """
    level_sep = '.'

    def render_table(self, table):
        """
        Serialize the table3.Table into the target format
        """
        raise NotImplementedError

    def render_exception(self, data, context):
        raise NotImplementedError
        
    def render(self, data, media_type=None, renderer_context=None):
        """
        Renders serialized *data* into target format
        """
        if 'response' in renderer_context and renderer_context['response'].exception:
            return self.render_exception(data, renderer_context)
        if data is None:
            return ''
        if 'results' in data:
            data = data['results']
        elif not isinstance(data, list):
            return ''
        table = self.tablize(data)
        result = self.render_table(table)
        return result

    def fast_tablize(self, data):
        if not isinstance(data, list):
            raise ValueError("fast_tablize needs a list of (nested) dicts!")            
        
        def _get_keys(item, prefix=()):
            for key, val in item.items():
                if isinstance(val, list):
                    raise ValueError("fast_tablize needs a list of (nested) dicts (not nested lists)!")            
                if isinstance(val, dict):
                    for nested_key, _type in _get_keys(val):
                        yield (key,) + nested_key, _type
                else:
                    yield (key,), type(val)    
                        
        def _get_val(d, key):
            val = d.get(key[0])
            if val is None or len(key) == 1:
                return val
            return _get_val(val, key[1:])

        keys = OrderedDict()
        for row in data:
            for key, _type in _get_keys(row):
                name = ".".join(key)
                if name in keys:
                    keys[name][1].add(_type)
                else:
                    keys[name] = (key, {_type})
                    
        table = table3.ObjectTable(rows=data)
        for col, (key, types) in keys.items():
            fieldtype = list(types)[0] if len(types) == 1 else None
            fieldtype = {bool:str, type(None):str}.get(fieldtype, fieldtype)
            table.add_column(label=col, col=partial(_get_val, key=key), fieldtype=fieldtype)

        return table
    
    def tablize(self, data):
        """
        Convert a list of data into a table.
        """
        # Currently first tries a relatively fast 'tablize' that doesn't deal with nested lists
        # falling back to the 'old' code if the data isnot a list of (nested) dicts
        #TODO: [WvA] do we actually need the old codepath, ie do we ever have nested lists?
        try:
            return self.fast_tablize(data)
        except ValueError:
            pass
        # First, flatten the data (i.e., convert it to a list of
        # dictionaries that are each exactly one level deep).  The key for
        # each item designates the name of the column that the item will
        # fall into.
        data = self.flatten_data(data)
        #import json; print(json.dumps(data, indent=2))
        # Get the set of all unique headers, and sort them.
        headers = OrderedDict()
        for item in data:
            for k, v in item.items():
                if k not in headers:
                    headers[k] = set()
                headers[k].add(type(v))
        table = table3.ObjectTable(rows=data)
        for header in headers:
            fieldtype = headers[header]
            if len(fieldtype) == 1:
                fieldtype = list(fieldtype)[0]
            else:
                fieldtype = None
            fieldtype = {bool:str, type(None):str}.get(fieldtype, fieldtype)
            table.add_column(label=header, col=partial(lambda key, item: item.get(key, None), header), fieldtype=fieldtype)
        return table


    def flatten_data(self, data):
        """
        Convert the given data collection to a list of dictionaries that are
        each exactly one level deep. The key for each value in the dictionaries
        designates the name of the column that the value will fall into.
        """
        flat_data = []
        for item in data:
            flat_item = self.flatten_item(item)
            flat_data.append(flat_item)
        return flat_data

    def flatten_item(self, item):
        if isinstance(item, list):
            flat_item = self.flatten_list(item)
        elif isinstance(item, dict):
            flat_item = self.flatten_dict(item)
        else:
            flat_item = {'': item}

        return flat_item

    def nest_flat_item(self, flat_item, prefix):
        """
        Given a "flat item" (a dictionary exactly one level deep), nest all of
        the column headers in a namespace designated by prefix.  For example:

         header... | with prefix... | becomes...
        -----------|----------------|----------------
         'lat'     | 'location'     | 'location.lat'
         ''        | '0'            | '0'
         'votes.1' | 'user'         | 'user.votes.1'

        """
        nested_item = {}
        for header, val in flat_item.items():
            nested_header = self.level_sep.join([prefix, header]) if header else prefix
            nested_item[nested_header] = val
        return nested_item

    def flatten_list(self, l):
        flat_list = {}
        for index, item in enumerate(l):
            index = str(index)
            flat_item = self.flatten_item(item)
            nested_item = self.nest_flat_item(flat_item, index)
            flat_list.update(nested_item)
        return flat_list

    def flatten_dict(self, d):
        flat_dict = OrderedDict()
        for key, item in d.items():
            key = str(key)
            flat_item = self.flatten_item(item)
            nested_item = self.nest_flat_item(flat_item, key)
            flat_dict.update(nested_item)
        return flat_dict


        
class CSVRenderer(TableRenderer):
    """
    Renderer which serializes to CSV
    """

    media_type = 'text/csv'
    format = extension = 'csv'

    def render_table(self, table):
        return table.to_csv()

    def render_exception(self, data, context):
        return data['detail']

    
    def render(self, data, media_type=None, renderer_context=None):
        import time; t = time.time()
        if renderer_context and renderer_context.get('fast_csv'):
            result = self.render_fast(data)
        else:
            result = super(CSVRenderer, self).render(data, media_type=media_type, renderer_context=renderer_context)
        logging.debug("Created csv in {t}s".format(t=time.time()-t))
        return result

    def render_fast(self, data):
        header = []
        out = StringIO()
        w = csv.writer(out)
        if 'results' not in data:
            return ""
        for d in data['results']:
            keys = set(d.keys())
            extra = keys - set(header)
            if extra:
                header += list(extra)
            row = [(str(d[h]).encode("utf-8") if h in d else "") for h in header]
            w.writerow(row)
        out_h = StringIO()
        csv.writer(out_h).writerow(header)
        return out_h.getvalue() + out.getvalue()
        
        
class CSVRendererWithUnderscores (CSVRenderer):
    level_sep = '_'

class XLSXRenderer(TableRenderer):
    """
    Renderer which serializes to Excel XLSX
    """

    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    format = extension = 'xlsx'

    def render_table(self, table):
        result = table.export(format='xlsx')
        return result

class SPSSRenderer(TableRenderer):
    """
    Renderer which serializes to Excel XLSX
    """

    media_type = 'application/x-spss-sav'
    format = 'spss'
    extension = 'sav'

    def render_table(self, table):
        result = table.export(format='spss')
        return result

class XHTMLRenderer(TableRenderer):
    """
    Renderer which serialises to HTML
    """
    media_type = 'application/html'
    format = 'xhtml'
    extension = 'html'

    def render_table(self, table):
        result = table.export(format='html')
        return result

class RdaRenderer(BaseRenderer):
    """
    Renderer which creates a .rda (R Data) file
    """
    
    media_type = 'application/x-r-rda'
    format = 'rda'
    extension = 'rda'

    def json_to_vectors(self, rows):
        result = {}
        n = len(rows)
        for i, row in enumerate(rows):
            for k, v in row.iteritems():
                if k not in result:
                    result[k] = [None] * n
                result[k][i] = v
        return result

    def render(self, data, media_type=None, renderer_context=None):
        try:
            if 'response' in renderer_context and renderer_context['response'].exception:
                data.update({'exception': True,
                             'status': renderer_context['response'].status_code})
            else:
                vectors = self.json_to_vectors(data['results'])
                data['results'] = create_dataframe(vectors.iteritems())
            return save_to_bytes(**data)
        except:
            logging.exception("Error on rendering to rda")
            raise
        
        
EXPORTERS = [CSVRenderer, XLSXRenderer, SPSSRenderer, XHTMLRenderer, RdaRenderer]
FORMAT_RENDERER_MAP = {renderer.format: renderer for renderer in EXPORTERS}

def set_response_content(response, format, filename="data"):
    """
    Add media type and content disposition to the response if applicable.
    Cannot be handled by the renderer since that returns data rather than a Response
    """
    if format in FORMAT_RENDERER_MAP:
        renderer = FORMAT_RENDERER_MAP[format]
        response['Content-Type'] = renderer.media_type
        response['Content-Disposition'] = 'attachment; filename="{}.{}"'.format(filename, renderer.extension)
    return response

