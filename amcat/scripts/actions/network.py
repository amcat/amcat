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
Script for creating a network graph from a table
"""

import logging; log = logging.getLogger(__name__)

from amcat.tools import dot
from django import forms
import csv
import itertools
from amcat.tools.table import table3, tableoutput
from amcat.scripts.script import Script
from django.http import HttpResponse


class Network(Script):
    """
    Make a network diagram from a list (table) of edges.
    The 'network' should consist of a csv-like string, without headers and
    delimited by comma, semicolon, or tab.
    Columns are subject and object (obligatory) and optional weight, quality, and subgraph (source).
    Example network:

    john,mary,3,-1
    mary,pete
    pete,john,,0.5
    john,mary,3,-1,pete
    mary,john,5,.25,pete
    """
    
    class options_form(forms.Form):
        network = forms.CharField(widget=forms.Textarea)
        normalize = forms.BooleanField(initial=False, required=False)
        green = forms.BooleanField(initial=False, required=False)
        bw = forms.BooleanField(label="Black & White", initial=False, required=False)
        
    def read_network(self, network):
        lines = network.split("\n")
        try:
            dialect = csv.Sniffer().sniff(network)
        except:
            for delimiter in ",;\t":
                if delimiter in network:
                    return csv.reader(lines, delimiter=delimiter)
        else:
            return csv.reader(network.split("\n"), dialect=dialect)

    def get_graph(self, r):
        g = dot.Graph()
        self.add_edges(r, g)
        if self.options['green']:
            g.theme.green = True
        elif self.options['bw']:
            g.theme = dot.BWDotTheme()
        return g
        
    def add_edges(self, r, graph):
        edges = []
        possible_header = True
        for line in r:
            print `line`
            if not line: continue
            su, obj = [x.strip() for x in line[:2]]
            if su == "subject" and obj == "object" and possible_header:
                possible_header = False
                continue # this is probably a header
            possible_header = False
            kargs = {}
            if len(line) > 2 and line[2].strip():
                kargs["weight"] = float(line[2])

            if len(line) > 3 and line[3].strip():
                kargs["sign"] = float(line[3])
                
            if len(line) > 4 and line[4].strip():
                kargs["graph"] = line[4]

            e = graph.addEdge(su, obj, **kargs)
            e.graph = kargs.get('graph', '')
            edges.append(e)

        if self.options['normalize']:
            max_weight = max(e.weight for e in edges)
            for e in edges:
                e.weight = float(e.weight) *10 / max_weight
        
    def _run(self, network):
        r = self.read_network(network)
        dot = self.get_dot(r)
        return dot.getHTMLObject()

    def get_response(self):
        r = self.read_network(self.options['network'])
        graph = self.get_graph(r)
        html = graph.getHTMLObject()
        dot = graph.getDot()
        edges = list(itertools.chain(*graph.edges.values()))
        t = table3.ObjectTable(rows=edges)
        def fmt(f, fmt="%1.1f"):
            if f is None: return ""
            return fmt % f
        t.addColumn(lambda e:e.subj.id, "subject")
        t.addColumn(lambda e:e.obj.id, "object")
        t.addColumn(lambda e:fmt(e.weight), "weight")
        t.addColumn(lambda e:fmt(e.sign, fmt="%+1.2f"), "quality")
        t.addColumn(lambda e:e.graph, "subgraph")

        html += tableoutput.table2html(t, printRowNames=False)
        
        html += "<pre>{dot}</pre>".format(**locals())
        return HttpResponse(html, status=200, mimetype="text/html")

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestArticle(amcattest.PolicyTestCase):
    pass
