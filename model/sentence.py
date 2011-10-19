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

from __future__ import print_function, absolute_import

from amcat.tools.model import AmcatModel

from django.db import models

class Sentence(AmcatModel):
    id = models.AutoField(primary_key=True, db_column="sentence_id")

    sentence = models.TextField()
    parnr = models.IntegerField()
    sentnr = models.IntegerField()

    article = models.ForeignKey("amcat.Article")

    #parsedSentences = ForeignKey(LB("ParsedSentence"), table="parses_words", distinct=True)

    def __unicode__(self):
        return self.sentence

    class Meta():
        db_table = 'sentences'
        app_label = 'amcat'
        
    def getAnalysedSentence(self, analysis):
        if type(analysis) <> int: analysis = analysis.id
        for a in self.parsedSentences:
            if analysis == a.analysis.id:
                return a


def cacheWords(sentences, words=True, lemmata=False, triples=False, sentiment=False, sentence=False):
    return

    """perword = dict(word = dict(string = []))

    if lemmata:
        perword["lemma"] = dict(lemma=["string"], pos=[])

    if sentiment:
        perword["lemma"] = dict(lemma=["string"], pos=[], sentiment=[], intensifier=[])

    what = dict(parsedSentences = dict(words={'word' : perword}))
    if triples:
        what["parsedSentences"] = ["triples"]

    if sentence:
        what["sentence"] = []

    cache(sentences, **what)"""
