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
This controller handles the analysis list and demo views
"""

from django import forms
from django.shortcuts import render
from api.rest.datatable import Datatable
from navigator.utils.auth import check

from amcat.models.analysis import Analysis, AnalysisSentence
from amcat.models.sentence import Sentence
from amcat.models.token import Triple
from amcat.tools.table.table3 import ObjectTable
from amcat.tools.table.tableoutput import table2htmlDjango
from amcat.tools.dot import Graph, Node, DotTheme

class DemoForm(forms.Form):
    sentence = forms.CharField()

@check(Analysis)
def demo(request, analysis):
    form = DemoForm(request.POST or None)

    if form.is_valid():
        s = analysis.get_script()
        sent = Sentence(id=-1, sentence=form.cleaned_data['sentence'])
        tokens, triples = s.process_sentence(sent)
        tokens = ObjectTable(rows=list(tokens),
                             columns=["position","word","lemma", "pos", "major","minor"])
        tokens_table = table2htmlDjango(tokens)

        words = dict((token.position, token.word) for token in tokens)

        if triples:
            triples = list(triples)
            dot = triples_to_dot(tokens, triples)
            triples_graph = dot.getHTMLObject()

            triples = ObjectTable(rows=list(triples))
            triples.addColumn("child", 'child position')
            triples.addColumn(lambda triple : words[triple.child], "child")
            triples.addColumn("parent", 'parent position')
            triples.addColumn(lambda triple : words[triple.parent], "parent")
            triples.addColumn("relation")
            triples_table = table2htmlDjango(triples)


    return render(request, 'navigator/analysis/demo.html', locals())


@check(AnalysisSentence)
def sentence(request, sentence):

    tokens = Datatable(TokenResource).filter(sentence=sentence).hide('sentence', 'id')
    triples = Datatable(TripleResource).filter(parent__sentence=sentence).hide('id')

    tokens_list = list(sentence.tokens.all())
    triples_list = list(Triple.objects.filter(parent__sentence=sentence))

    graph = triples_to_dot(tokens_list, triples_list)
    dot = graph.getDot()
    triples_graph = graph.getHTMLObject()
    
    return render(request, 'navigator/analysis/sentence.html', locals())

def triples_to_dot(tokens, triples):
    g = Graph()
    for token in tokens:
        g.addNode(Node(id=token.position, label="%i:%s" % (token.position, token.word)))
    for triple in triples:
        g.addEdge(triple.child.position, triple.parent.position, label=triple.relation)
    g.theme.graphattrs["rankdir"] = "BT"
    g.theme.shape = "none"
    g.theme.arrows = False
    g.theme.edgesize = 10


    return g
