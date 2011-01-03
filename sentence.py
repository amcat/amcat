from __future__ import unicode_literals, print_function, absolute_import
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
Object-layer module containing classes modelling sentences
"""

import toolkit
from cachable2 import Cachable, DBProperty, ForeignKey, DBProperties, cache
import article, parsedsentence

class Sentence(Cachable):
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'sentence'
    __dbproperties__ = ["parnr", "sentnr", "encoding"]

    sentence, parnr, sentnr = DBProperties(3)

    article = DBProperty(lambda:article.Article)
    parsedSentences = ForeignKey(lambda:parsedsentence.ParsedSentence, table="parses_words", distinct=True)
        
    def getAnalysedSentence(self, analysis):
        if type(analysis) <> int: analysis = analysis.id
        for a in self.analysedSentences:
            if analysis == a.analysisid:
                return a


def cacheWords(sentences, words=True, lemmata=False, triples=False, sentiment=False, sentence=False):
    perword = dict(word = dict(string = []))
    if lemmata: perword["lemma"] = dict(lemma=["string"], pos=[])
    if sentiment: perword["lemma"] = dict(lemma=["string"], pos=[], sentiment=[], intensifier=[])
    what = dict(parsedSentences = dict(words={'word' : perword}))
    if triples: what["parsedSentences"] = ["triples"]
    if sentence: what["sentence"] = []
    print(what)
    cache(sentences, **what)
        
