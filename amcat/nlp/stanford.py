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
Preprocess using the Stanford dependency parser 
See http://nlp.stanford.edu/software/lex-parser.shtml
"""

import logging, re, itertools
log = logging.getLogger(__name__)

from xml.etree import ElementTree
from amcat.models.token import TokenValues, TripleValues
from amcat.models import AnalysisSentence, Token

from amcat.nlp.analysisscript import VUNLPParser
from amcat.nlp import sbd, wordcreator
CMD = "Stanford-CoreNLP"

class StanfordParser(VUNLPParser):
    parse_command = CMD

        

    def store_parse(self, analysed_article, data):
        if data.startswith("CoreNLP failed"):
            raise Exception(data)
        
        root = ElementTree.fromstring(data)
        # if the analysis sentences already exist, check there are no tokens and line the analysis_sentence up.
        # otherwise, create new ones
        sentences = list(sbd.get_or_create_sentences(analysed_article.article))
        if AnalysisSentence.objects.filter(analysed_article=analysed_article).exists():
            if Token.objects.filter(sentence__analysed_article=analysed_article).exists():
                raise Exception("Article already has tokens!")
            analysis_sentences = [AnalysisSentence.objects.get(analysed_article=analysed_article, sentence=sentence).id
                                  for sentence in sentences]
        else:
            analysis_sentences = [AnalysisSentence.objects.create(analysed_article=analysed_article, sentence=sentence).id
                                  for sentence in sentences]
        result = interpret_xml(analysis_sentences, root)
        import pickle; pickle.dump(result[1], open("/tmp/triples", "w"))
        wordcreator.store_analysis(analysed_article, *result)

        
def interpret_xml(analysis_sentence_ids, root):
    all_tokens, all_triples = [], []
    for sentence_xml in root.find("./document/sentences").iter("sentence"):
        analysis_sentence_id = analysis_sentence_ids[int(sentence_xml.get("id")) - 1] # corenlp has 1-based offset
        tokens, triples = interpret_sentence(analysis_sentence_id, sentence_xml)
        all_tokens.append(tokens)
        all_triples.append(triples)
    corefsets = interpret_coreferences(analysis_sentence_ids, root)
    triples = list(itertools.chain(*all_triples))
    return itertools.chain(*all_tokens), triples, corefsets

def interpret_sentence(analysis_sentence_id, sentence_xml):
    tokens = [get_token(analysis_sentence_id, t) for t in sentence_xml.iter("token")]
    dependencies = sentence_xml.find("collapsed-ccprocessed-dependencies").iter("dep")
    triples = [get_triple(analysis_sentence_id, t) for t in dependencies]
    return tokens, triples

def interpret_coreferences(analysis_sentence_ids, root):
    coref = root.find("./document/coreference")
    if coref:
        return (interpret_coreference(analysis_sentence_ids, corefset_xml)
                for corefset_xml in root.find("./document/coreference").findall("coreference"))


def interpret_coreference(analysis_sentence_ids, coref):
    for mention in coref.iter("mention"):
        analysis_sentence_id = analysis_sentence_ids[int(mention.find("sentence").text) -1]
        yield (analysis_sentence_id, int(mention.find("head").text)-1)
    
def get_triple(analysis_sentence_id, triple):
    def offset(name):
        return int(triple.find(name).get("idx")) - 1
    return TripleValues(analysis_sentence_id, offset("dependent"), offset("governor"), triple.get("type"))

def get_token(analysis_sentence_id, token):
    #TokenValues = namedtuple("TokenValues", ["analysis_sentence", "position", "word", "lemma", "pos", "major", "minor", "namedentity"])
    pos_major = token.find("POS").text
    pos = POSMAP[pos_major]
    ner = token.find("NER").text
    ner = NERMAP[ner] if ner != 'O' else None
    return TokenValues(analysis_sentence_id, int(token.get("id")) - 1,
                       token.find("word").text, token.find("lemma").text,
                       pos, pos_major, None, ner)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestStanford(amcattest.PolicyTestCase):

    @classmethod
    def _get_test_xml(cls):
        import os.path, amcat
        data = open(os.path.join(os.path.dirname(amcat.__file__), "tests", "testfile_stanford.xml")).read()
        return ElementTree.fromstring(data)
    
    def test_interpret_xml(self):
        # <!-- Mary met John. She likes him. -->
        analysis_sentences=range(10)
        tokens, triples, corefsets = interpret_xml(analysis_sentences, self._get_test_xml())
        self.assertEqual(set(tokens), {
                TokenValues(0, 0, 'Mary', 'Mary', 'N', "NNP", None, 'PERSON'),
                TokenValues(0, 1, 'met', 'meet', 'V', "VBD", None, None),
                TokenValues(0, 2, 'John', 'John', 'N', "NNP", None, 'PERSON'),
                TokenValues(1, 0, 'She', 'she', 'O', "PRP", None, None),
                TokenValues(1, 1, 'likes', 'like', 'V', "VBZ", None, None),
                TokenValues(1, 2, 'him', 'he', 'O', "PRP", None, None),
                })

        self.assertEqual(set(triples), {
                TripleValues(0, 0, 1, "nsubj"),
                TripleValues(0, 2, 1, "dobj"),
                TripleValues(1, 0, 1, "nsubj"),
                TripleValues(1, 2, 1, "dobj"),
                })


        self.assertEqual({frozenset(coref) for coref in corefsets}, {
                frozenset([(0,0), (1,0)]),
                frozenset([(0,2), (1,2)])})

                
 
###########################################################################
#                        U G L Y   C O N S T A N T                        #
###########################################################################

POSMAP = {
   '$' :'.',
   '"' :'.',
    "'" :'.',
   '``' : '.',
   "''" : '.',
   '(' :'.',
   ')' :'.',
   '-LRB-' : '.',
   '-RRB-' : '.',
   ',' :'.',
   '--' :'.',
   '.' :'.',
   ':' :'.',
   'CC' :'C',
   'CD' :'Q',
   'DT' :'D',
   'EX' :'R',
   'FW' :'?',
   'IN' :'P',
   'JJ' :'A',
   'JJR' :'A',
   'JJS' :'A',
   'LS' :'Q',
   'MD' :'V',
   'NN' :'N',
   'NNP' :'N',
   'NNPS' :'N',
   'NNS' :'N',
   'PDT' :'D',
   'POS' :'O',
   'PRP' :'O',
   'PRP$' :'O',
   'RB' :'B',
   'RBR' :'B',
   'RBS' :'B',
   'RP' :'R',
   'SYM' :'.',
   'TO' :'R',
   'UH' :'I',
   'VB' :'V',
   'VBD' :'V',
   'VBG' :'V',
   'VBN' :'V',
   'VBP' :'V',
   'VBZ' :'V',
   'WDT' :'D',
   'WP' :'O',
   'WP$' :'O',
   'WRB' :'B',
    }
NERMAP = {
    'LOCATION' : 'L',
    'ORGANIZATION' : 'O',
    'PERSON' : 'P',
    'DATE' : 'D',
    'DURATION' : 'D',
    'TIME' : 'D',
    'NUMBER' : '#',
    'ORDINAL' : '#',
    'MISC' : '?',
    'MONEY' : '#',
    'SET' : '#',
    'PERCENT' : '#',
    }



if __name__ == '__main__':
    from django.db import transaction
    from amcat.models import AnalysedArticle
    aa = AnalysedArticle.objects.get(pk=1215)
    parse = open("/tmp/aa_1215.xml").read()
    with transaction.commit_on_success():
        StanfordParser().store_parse(aa, parse)
