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
Preprocess using Mate german
See http://code.google.com/p/mate-tools/.
"""
import logging
log = logging.getLogger(__name__)

import requests, rdflib, collections
from amcat.models.token import TokenValues, TripleValues
from amcat.nlp import sbd, wordcreator
from amcat.models import AnalysisSentence, AnalysedArticle

RDF = rdflib.Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
GSTRUCT = rdflib.Namespace("http://cs.lth.se/ontologies/gstruct.owl#")

from amcat.nlp.analysisscript import AnalysisScript

class Mate(AnalysisScript):
    def submit_article(self, article):
        plugin = self.get_plugin()
        if isinstance(article, AnalysedArticle):
            # (re)set done, error, info
            article.done = False
            article.error = False
            article.save()
        else:
            # Create AnalysedArticle object
            article = AnalysedArticle.objects.create(article=article, plugin=plugin,
                                                     done=False, error=False)
        return article
    
    def _do_retrieve_article(self, analysed_article):
        for sentence in sbd.get_or_create_sentences(analysed_article.article):
            asent = AnalysisSentence.objects.create(analysed_article=analysed_article, sentence=sentence)            
            log.debug("Parsing {asent.id} : {asent.sentence.sentence!r}".format(**locals()))
            add_sentence(asent)
        return True
            
def parse_rdf(rdf):
    """
    Parses the mate rdf output and returns a (sentences, words) pair, where
    - sentences is an ordered list of sentence ids
    - words is a list of {sentence: .., pos: .., ...} word representations
    """ 
    sentence_inx = {} # index : sentence  
    objs = collections.defaultdict(dict) # word : {sentence=x, pos=x, ...}

    word_ids = set()
    pred_ids = set()
    
    g = rdflib.Graph()
    g.parse(rdf, format="n3")
    for subject,predicate,obj in g:
        if predicate == RDF["type"]:
            continue # don't need type info
        if not predicate.startswith(GSTRUCT):
            raise Exception("Unknown predicate: {predicate}".format(**locals()))
        
        predicate = predicate[len(GSTRUCT):]

        
        if predicate == "words":
            objs[obj]["sentence"] = unicode(subject)
            word_ids.add(obj)
        elif predicate == "inx":
            sentence_inx[int(obj)] = unicode(subject)
        else:
            objs[subject][predicate] = unicode(obj)

    words = [objs[wid] for wid in word_ids]
    
            
    return ([sentence_inx[inx] for inx in sorted(sentence_inx)],
            sorted(words, key=lambda word : (word["sentence"], word["id"])))

POSMAP = [
    # prefixes of pos tags and 'amcat' pos-letters
    # based on: A Brief Introduction to the TIGER Treebank
    ("V", "V"),
    ("ADJ", "A"),
    ("ADV", "B"),
    ("AP", "P"),
    ("DET", "D"),
    ("ART", "D"),
    ("CARD", "Q"),
    ("FM", "?"),
    ("ITJ", "?"),
    ("K", "C"),
    ("NN", "N"),
    ("NE", "M"),
    ("PAV", "B"),
    ("PT", "R"),
    ("P", "O"),
    ("S", "?"),
    ("T", "?"),
    ("X", "?"),
    ("$", "."),
    ]

    
def map_pos(pos):
    for pref, p in POSMAP:
        if pos.startswith(pref):
            return p
    raise Exception("Unknown POS: {pos}".format(**locals()))

def create_values(sid, words):
    tokens = []
    triples = []
    for word in words:
        tokens.append(TokenValues(sid, int(word["id"]), word["form"], word["lemma"], map_pos(word["pos"]), word["pos"], None, None))
        head = int(word["head"])
        if head:
            triples.append(TripleValues(sid, int(word['id']), head, word['deprel']))
    return tokens, triples

def get_rdf(sent):
    data= dict(sentence=sent,
               returnType="rdf",
               )
    r = requests.post("http://parser.vanatteveldt.com/parse", data=data, stream=True)
    return r.raw

def add_sentence(asent):
    rdf = get_rdf(asent.sentence.sentence)
    sentences, words = parse_rdf(rdf)
    tokens, triples = create_values(asent.id, words)
    wordcreator.store_analysis(asent.analysed_article, tokens, triples)




