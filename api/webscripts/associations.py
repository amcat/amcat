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

from webscript import WebScript

from amcat.scripts.searchscripts.articlelist import ArticleListScript
from django import forms
from amcat.tools.table import table3
from amcat.tools import dot, keywordsearch, amcates
import re
import logging
import collections
import datetime
from django.template.loader import render_to_string
import json
from django.http import HttpResponse

log = logging.getLogger(__name__)

FORMATS = [
    ("0.12", False, "%1.2f"),
    ("0.123", False, "%1.3f"),
    ("12%", True, "%1.0f%%"),
    ("12.3%", True, "%1.1f%%"),
    ]

INTERVALS = [(None, "None"), ("year", "Year"), ("month", "Month"), ("week", "Week")]

class AssociationsForm(forms.Form):
    network_output = forms.ChoiceField(choices=[('oo', 'Table'),
                                        ('oon', 'Network graph'),
                                        ])

    association_format = forms.ChoiceField(label="Number Format", choices = ((i, x[0]) for (i,x) in enumerate(FORMATS)), initial=0)
    
    graph_threshold = forms.DecimalField(label="Graph: threshold", required=False)
    graph_label = forms.BooleanField(label="Graph: include association in label", required=False)

    condprob = forms.BooleanField(label="Weigh for number of hits", required=False)

    interval = forms.ChoiceField(label="Interval", choices = INTERVALS, initial=0)
    
class ShowAssociations(WebScript):
    name = "Associations"
    form_template = None
    form = AssociationsForm
    output_template = None
    solrOnly = True
    displayLocation = ('ShowSummary','ShowArticleList')
    output_type = table3.Table

    def format(self, a):
        name, perc, formatstr = FORMATS[int(self.options["association_format"])]
        if a:
            if perc: a*=100
            return formatstr % (a,)

    @property
    def _interval(self):
        interval = self.data.get('interval', None)
        if interval == 'None': interval = None
        return interval
            
    def get_probs(self):
        """
        Get the probability scores for each article.
        Yields a sequence of (interval, query, id, score) tuples.
        """
        filters = dict(keywordsearch.filters_from_form(self.data))
        queries = list(keywordsearch.queries_from_form(self.data))

        condprob = self.data.get('condprob', None)
        if condprob == 'False': condprob = False
        
        score_func = _condprob if condprob else None
        interval_func = getattr(Intervals, self._interval) if (self._interval) else None
        qargs = dict(filters=filters, score=(score_func is not None),
                     fields=(["date"] if interval_func else []))

        
        es = amcates.ES()
        for q in queries:
            for r in es.query_all(query=q.query, **qargs):
                s = score_func(r.score) if score_func else 1
                i = interval_func(r.date) if interval_func else None
                yield i, q, r.id, s

    def get_table(self):
        probs = collections.defaultdict(lambda : collections.defaultdict(dict))
        for (i, q, id, s) in self.get_probs():
            probs[i][q.label][id] = s


        
        assocTable = table3.ListTable(colnames=["Interval", "From", "To", "Association"])
        for i in sorted(probs):
            for q in probs[i]:
                sumprob1 = float(sum(probs[i][q].values()))
                if sumprob1 == 0: continue
                for q2 in probs[i]:
                    if q == q2: continue
                    sumproduct = 0
                    for id, p1 in probs[i][q].iteritems():
                        p2 = probs[i][q2].get(id)
                        if not p2: continue
                        sumproduct += p1*p2
                    p = sumproduct / sumprob1
                    assocTable.addRow(i, q, q2, p)
        return assocTable
                
    def run(self):
        assocTable = self.get_table()
        intervals = sorted({i for (i,q,q2,p) in assocTable})
        
        if self.options['network_output'] == 'ool':
            self.output = 'json-html'
            assocTable = table3.WrappedTable(assocTable, cellfunc = lambda a: self.format(a) if isinstance(a, float) else a)
            
            return self.outputResponse(assocTable, self.output_type)
        elif self.options['network_output'] == 'oo':
            if self._interval:
                cols = {}
                assocs = {(x,y) for (i,x,y,s) in assocTable}
                cols = {u"{x}\u2192{y}".format(x=x, y=y) : (x,y) for (x,y) in assocs}
                
                def cn(colname):
                    return colname.replace(u"\u2192", "_")
                    
                colnames = sorted(cols)
                columns = [{"sTitle": "x", "sWidth": "100px", "sType": "objid", "mDataProp": "x"}]
                columns += [{"mData": cn(colname), "sTitle": colname, "sWidth": "70px", "mDataProp": cn(colname)} for colname in colnames]
                
                data = []
                scores = {(i,x,y) : self.format(s) for (i,x,y,s) in assocTable}
                for i in intervals:
                    row = {"x" : i}
                    for c in colnames:
                        row[cn(c)] = scores.get((i, ) + cols[c], 0)
                    data.append(row)

                form_proxy = dict(
                    outputType={"data" : "table"},
                    dateInterval={"data" : self._interval},
                    xAxis={"data" : "date"},
                    yAxis={"data" : "searchTerm"}
                    )


                scriptoutput = render_to_string('api/webscripts/aggregation.html', {
                    'dataJson':json.dumps(data),
                    'columnsJson':json.dumps(columns),
                    'aggregationType':'association',
                    'datesDict': json.dumps({}),
                    'graphOnly': 'false',
                    'labels' : '{}',
                    'ownForm': form_proxy,
                    'relative': '1',
                })

                return self.outputJsonHtml(scriptoutput)
            else:
                # convert list to dict and make into dict table
                result = table3.DictTable()
                result.rowNamesRequired=True
                for i,x,y,a in assocTable:
                    result.addValue(x,y,self.format(a))
                result.columns = sorted(result.columns)
                result.rows = sorted(result.rows)
                self.output = 'json-html'
                res =  self.outputResponse(result, self.output_type)
                return res
        elif self.options['network_output'] == 'oon':
            html = ""
            for interval in intervals:
                g = dot.Graph()
                threshold = self.options.get('graph_threshold')
                if not threshold: threshold = 0
                nodes = {}
                def getnode(x):
                    if not x in nodes: 
                        id = "node_%i_%s" % (len(nodes), re.sub("\W","",x))
                        nodes[x] = dot.Node(id, x)
                    return nodes[x]

                for i, x,y,a in assocTable:
                    if i != interval:
                        continue
                    if threshold and a < threshold:
                        continue

                    opts = {}
                    if self.options['graph_label']: opts['label'] = self.format(a)
                    w = 1 + 10 * a

                    g.addEdge(getnode(x),getnode(y), weight=w, **opts)
                if interval is not None:
                    html += "<h1>{interval}</h1>".format(**locals())
                g.normalizeWeights()
                html += g.getHTMLObject()
            self.output = 'json-html'
            return self.outputResponse(html, unicode)
            

class Intervals(object):
    @classmethod
    def year(cls, d):
        return "{d.year}-01-01".format(**locals())
    @classmethod
    def month(cls, d):
        return "{d.year}-{d.month:02}-01".format(**locals())
    @classmethod
    def quarter(cls, d):
        q = 1 + (d.month-1)/3
        return "{d.year}-{q}".format(**locals())
    @classmethod
    def week(cls, d):
        d = d + datetime.timedelta(days=-d.weekday())
        return "{d.year}-{d.month:02}-{d.day:02}".format(**locals())

        
def _condprob(f):
    return 1 - (.5 ** f)
