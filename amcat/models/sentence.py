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
    """Model for sentences.

    A sentence is a natural sentence in an article
    created by sentence boundary detection. Manual coding and preprocessing
    is often based on sentences
    """
    __label__ = 'sentence'
    
    id = models.AutoField(primary_key=True, db_column="sentence_id")
    sentence = models.TextField()
    parnr = models.IntegerField()
    sentnr = models.IntegerField()
    article = models.ForeignKey("amcat.Article", related_name='sentences')

    class Meta():
        db_table = 'sentences'
        app_label = 'amcat'
        unique_together = ('article', 'parnr', 'sentnr')
        ordering = ['article', 'parnr', 'sentnr']

    def get_triples(self, analysis):
        from amcat.models.analysis import Triple
        return Triple.objects.filter(parent__sentence=self, analysis=analysis)


    
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestSentence(amcattest.PolicyTestCase):

    def test_get_sentences(self):
        """Test retrieving all (unicode) sentences for an article"""
        a = amcattest.create_test_article()
        sentences = []
        for i, offset in enumerate(range(22, 20000, 1000)):
            sentnr = i % 7
            parnr = i // 7
            sent = "".join(unichr(offset + c) for c in range(47, 1000, 100))
            sentences += [(parnr, sentnr, sent)]
            Sentence.objects.create(article = a, parnr = parnr, sentnr = sentnr, sentence=sent)
        from amcat.models.article import Article
        aid = a.id
        del a
        a2 = Article.objects.get(pk = aid)
        sentences2 = [(s.parnr, s.sentnr, s.sentence) for s in a2.sentences.all()]

        self.assertEqual(set(sentences), set(sentences2))

            
            
            
        
