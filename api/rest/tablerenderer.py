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

from collections import OrderedDict
from functools import partial

from rest_framework.renderers import *
from amcat.tools.table import table3


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
        return self.render_table(table)

    def tablize(self, data):
        """
        Convert a list of data into a table.
        """
        # First, flatten the data (i.e., convert it to a list of
        # dictionaries that are each exactly one level deep).  The key for
        # each item designates the name of the column that the item will
        # fall into.
        data = self.flatten_data(data)

        # Get the set of all unique headers, and sort them.
        headers = OrderedDict()
        for item in data:
            for k, v in item.iteritems():
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
            table.addColumn(label=header, col=partial(lambda key, item: item.get(key, None), header), fieldtype=fieldtype)

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
        for header, val in flat_item.iteritems():
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
        for key, item in d.iteritems():
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


        
EXPORTERS = [CSVRenderer, XLSXRenderer, SPSSRenderer, XHTMLRenderer]

def set_response_content(response):
    """
    Add media type and content disposition to the response if applicable.
    Cannot be handled by the renderer since that returns data rather than a Response
    """
    for exporter in EXPORTERS:
        if response.accepted_media_type == exporter.media_type:
            response['Content-Type'] = response.accepted_media_type
            response['Content-Disposition'] = 'attachment; filename="data.{exporter.extension}"'.format(**locals())
            break
    return response
