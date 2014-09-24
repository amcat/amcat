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
Interface with the xtas NLP processing system
"""
from amcat.tools import amcates

class ANALYSES:
    postag = [{"module" : "xtas.tasks.single.tokenize"},
              {"module": "xtas.tasks.single.pos_tag",
               "arguments" : {"model" : "nltk"}}]

    corenlp = [{"module" : "xtas.tasks.single.corenlp"}]
    alpino = [{"module" : "xtas.tasks.single.alpino"}]
    sources_nl = [{"module" : "xtas.tasks.single.alpino"},
                  {"module" : "xtas.tasks.single.sources_nl"}]
    tadpole = [{"module" : "xtas.tasks.single.tadpole"}]
    corenlp_lemmatize = [{"module" : "xtas.tasks.single.corenlp_lemmatize"}]

    semafor = [{"module" : "xtas.tasks.single.corenlp"},
               {"module" : "xtas.tasks.single.semafor"}]
    sources_en = [{"module" : "xtas.tasks.single.corenlp"},
                  {"module" : "xtas.tasks.single.semafor"},
                  {"module" : "xtas.tasks.single.sources_en"}]
    clauses_en = [{"module" : "xtas.tasks.single.corenlp"},
                  {"module" : "xtas.tasks.single.sources_en"},
                  {"module" : "xtas.tasks.single.clauses_en"}]

def _get_analysis(analysis):
    """Convert analysis name into list of actions"""
    if isinstance(analysis, list):
        return analysis
    elif hasattr(ANALYSES, analysis):
        return getattr(ANALYSES, analysis)
    elif "." in analysis:
        return [{"module" : m} for m in analysis.split('__')]
    else:
        raise ValueError("Unknown analysis: {analysis}".format(**locals()))

def get_result(article, analysis, store_intermediate=True, block=True):
    from xtas.tasks.pipeline import pipeline
    if not isinstance(article, int): article = article.id
    analysis = _get_analysis(analysis)

    es = amcates.ES()
    doc = {'index': es.index, 'type': es.doc_type,
           'id': article, 'field': 'text'}
    r = pipeline(doc, analysis,
                 store_intermediate=store_intermediate)
    return r

def get_adhoc_result(analysis, text, store_intermediate=True):
    from xtas.tasks.es import adhoc_document
    from xtas.tasks.pipeline import pipeline

    analysis = _get_analysis(analysis)
    es = amcates.ES()
    doc = adhoc_document('adhoc', es.doc_type, 'text', text=text)

    print "Pipelining..."
    return pipeline(doc, analysis, store_intermediate=store_intermediate)
