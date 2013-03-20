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
Model module for the Preprocessing queue

Articles on the preprocessing queue need to be checked to see if preprocessing
needs to be done.

See http://code.google.com/p/amcat/wiki/Preprocessing
"""
from __future__ import unicode_literals, print_function, absolute_import

from django.db import models, transaction
 
from amcat.tools.model import AmcatModel
from amcat.tools.djangotoolkit import receiver
from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle, ArticleSet
from amcat.models.token import Token, Triple, Relation
from amcat.models.language import Language
from amcat.models.plugin import Plugin
from amcat.models.project import Project
from amcat.models.sentence import Sentence
from amcat.tools.djangotoolkit import get_or_create

from django.db.models.signals import post_save, post_delete
from django.db.models import Q

import logging; log = logging.getLogger(__name__)

class AnalysedArticle(AmcatModel):
    """
    The analysed article table keeps track of which articles are (being) preprocessed.

    The analysed article can be in one of three states:
    done  -> the article is successfully preprocessed. The info field is meaningless.
    error -> something went wrong preprocessing the article. The info field contains
                  the log / error message, if available.
    ~done & ~error -> the article is being preprocessed. The info field is optionally used
                      by the preprocessing plugin.
    (done & error makes no sense, but two booleans is still nicer than some sort of enumeration)
    """

    id = models.AutoField(primary_key=True, db_column="article_analysis_id")

    article = models.ForeignKey(Article)
    plugin = models.ForeignKey("amcat.Plugin")
    
    done = models.BooleanField(default=False)
    error = models.BooleanField(default=False)
    info = models.TextField(null=True)

    class Meta():
        db_table = 'analysed_articles'
        app_label = 'amcat'
        unique_together = ('article', 'plugin')

        
class AnalysisSentence(AmcatModel):
    """
    Explicity many-to-many sentence - analysisarticle
    """
    id = models.AutoField(primary_key=True)
    analysed_article = models.ForeignKey(AnalysedArticle, related_name="sentences")
    sentence = models.ForeignKey(Sentence, related_name="analyses")
    
    class Meta():
        app_label = 'amcat'
        db_table = "analysis_sentences"
        unique_together = ('analysed_article', 'sentence')

    def _get_tokens(self, get_words=False):
        tokens = Token.objects.filter(sentence=self).select_related("word", "word__lemma")
        self._tokendict = dict((t.position, t) for t in tokens)
        return self._tokendict
        
    @property
    def tokendict(self):
        try:
            return self._tokendict
        except AttributeError:
            return self._get_tokens()

    def get_token(self, position):
        return self.tokendict[position]
        
    @property
    def triples(self):
        return list(Triple.objects.filter(parent__sentence=self).select_related("parent", "child", "relation"))
        
    def __int__(self):
        return self.id
