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
import logging

from amcat.tools import amcates


class ANALYSES:
    corenlp = [{"module" : "xtas.tasks.single.corenlp"}]
    parzu = [{"module" : "xtas.tasks.single.parzu"}]
    alpino = [{"module" : "xtas.tasks.single.alpino"}]
    sources_nl = [{"module" : "xtas.tasks.single.alpino"},
                  {"module" : "xtas.tasks.single.sources_nl"}]
    clauses_nl = [{"module" : "xtas.tasks.single.alpino"},
                  {"module" : "xtas.tasks.single.sources_nl"},
                  {"module" : "xtas.tasks.single.clauses_nl"}]


    frog = [{"module" : "xtas.tasks.single.frog"}]

    corenlp_lemmatize = [{"module" : "xtas.tasks.single.corenlp_lemmatize"}]

    sources_en = [{"module" : "xtas.tasks.single.corenlp"},
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

def _get_doc(article):
    if not isinstance(article, int): article = article.id
    es = amcates.ES()
    return {'index': es.index, 'type': es.doc_type,
           'id': article, 'field': 'text'}

def get_preprocessed_results(articles, analysis):
    """
    Get only the results that have already been preprocessed
    Returns a sequence of id, result pairs for the articles that were found
    """
    ids = [(art if isinstance(art, int) else art.id) for art in articles]
    analysis = _get_analysis(analysis)
    doc_type = _get_doc_type(analysis)
    for d in amcates.ES().mget(ids, doc_type=doc_type, parents=ids):
        if d['found']:
            yield int(d['_id']), d['_source']
    
    
def get_results(articles, analysis, store_intermediate=True):
    from xtas.tasks.pipeline import pipeline_multiple
    docs = [_get_doc(a) for a in articles]
    analysis = _get_analysis(analysis)

    r = pipeline_multiple(docs, analysis, store_intermediate=store_intermediate)
    for id, result in r.items():
        if result['state'] != 'SUCCESS':
            raise Exception("Exception on processing article {id}: {msg}"
                            .format(msg=result['result'], **locals()))
        yield id, result['result']

def _get_doc_type(analysis):
    analysis = _get_analysis(analysis)
    pipeline = [task['module'].split(".")[-1] for task in analysis]
    return "__".join(["article"] + pipeline)


def get_result(article, analysis, store_intermediate=True):
    from xtas.tasks.pipeline import pipeline
    analysis = _get_analysis(analysis)
    r = pipeline(_get_doc(article), analysis,
                 store_intermediate=store_intermediate)
    return r

def get_adhoc_result(analysis, text, store_intermediate=True):
    from xtas.tasks.es import adhoc_document
    from xtas.tasks.pipeline import pipeline

    analysis = _get_analysis(analysis)
    es = amcates.ES()
    doc = adhoc_document('adhoc', es.doc_type, 'text', text=text)

    return pipeline(doc, analysis, store_intermediate=store_intermediate)

def preprocess_set_background(articleset, analysis, limit=None, **kargs):
    analysis = _get_analysis(analysis)
    doc_type = _get_doc_type(analysis)
    aids = list(amcates.ES().get_articles_without_child(doc_type, sets=articleset, limit=limit))
    logging.warning("Adding {} articles from set {} to background queue".format(len(aids), articleset))
    preprocess_background(aids, analysis)

    
def preprocess_background(articles, analysis, store_intermediate=True):
    from xtas.tasks.pipeline import pipeline_multiple
    docs = [_get_doc(a) for a in articles]
    analysis = _get_analysis(analysis)

    r = pipeline_multiple(docs, analysis, store_intermediate=store_intermediate, block=False, queue="background")
    return r




def _create_mapping(child_type, properties):
    body = {child_type: {"_parent": {"type": "article"},
                         "properties" : {prop :{"type" : "object", "enabled" : False}
                                         for prop in properties}}}
    amcates.ES().put_mapping(doc_type=child_type, body=body)
    
def check_mappings():
    """Make sure the needed parent mappings are active"""
    for name, analysis in ANALYSES.__dict__.items():
        if name.startswith("__"): continue
        for i in range(len(analysis)):
            child_type = _get_doc_type(analysis[:i+1])
            if not amcates.ES().exists_type(child_type):
                mod = analysis[i]['module']
                from amcat.tools.classtools import import_attribute
                try:
                    t = import_attribute(mod)
                except ImportError:
                    logging.exception("Cannot create mapping {child_type}: Cannot find task {mod}"
                                 .format(**locals()))
                    continue
                try:
                    properties = t.output
                except AttributeError:
                    logging.exception("Cannot create mapping {child_type}: Task {mod} has no output attribute"
                                 .format(**locals()))
                    continue
                logging.info("Creating parent mapping article -> {child_type} (properties: {properties})"
                             .format(**locals()))
                _create_mapping(child_type, properties)
                
