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

    semafor = [{"module" : "xtas.tasks.single.corenlp"},
               {"module" : "xtas.tasks.single.semafor"}]

def get_result(article, analysis, store_intermediate=True, block=True):
    from xtas.tasks.pipeline import pipeline
    if not isinstance(article, int): article = article.id
    if not isinstance(analysis, list):
        if hasattr(ANALYSES, analysis):
            analysis = getattr(ANALYSES, analysis)
        elif "." in analysis:
            analysis = [{"module" : m} for m in analysis.split('__')]
        else:
            raise ValueError("Unknown analysis: {analysis}".format(**locals()))

    es = amcates.ES()
    doc = {'index': es.index, 'type': es.doc_type,
           'id': article, 'field': 'text'}
    r = pipeline(doc, analysis,
                 store_intermediate=store_intermediate, block=block)
    return r
