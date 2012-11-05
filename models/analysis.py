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


class Analysis(AmcatModel):
    """Object representing an NLP 'preprocessing' analysis"""
    id = models.AutoField(db_column='analysis_id', primary_key=True)
    language = models.ForeignKey(Language)
    sentences = models.BooleanField(default=True)
    plugin = models.ForeignKey(Plugin, null=True)

    def get_script(self, **options):
        try:
            return self.plugin.get_instance(analysis=self, **options)
        except TypeError:
            return self.plugin.get_instance(**options)

    class Meta():
        db_table = 'analyses'
        app_label = 'amcat'

    def __unicode__(self):
        return self.plugin.label if self.plugin else "No plugin available"

class AnalysisArticle(AmcatModel):
    """
    The Article Analysis table keeps track of which articles are / need to be preprocessed
    """

    id = models.AutoField(primary_key=True, db_column="article_analysis_id")

    article = models.ForeignKey(Article)
    analysis = models.ForeignKey(Analysis)
    started= models.BooleanField(default=False)
    done = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)

    class Meta():
        db_table = 'analysis_articles'
        app_label = 'amcat'
        unique_together = ('article', 'analysis')

    def do_store_analysis(self, tokens, triples=None):
        """
        Store the given tokens and triples for this articleanalysis, setting
        it to done=True if stored succesfully.
        """
        if self.done: raise Exception("Cannot store analyses when already done")
        from amcat.nlp.wordcreator import create_triples
        result = create_triples(tokens, triples)
        self.done = True
        self.save()
        return result

        
    @transaction.commit_on_success
    def store_analysis(self, tokens, triples=None):
        """
        Store the given tokens and triples using do_store_analysis, wrapping it
        inside a transaction
        """
        self.do_store_analysis(tokens, triples)
        
class AnalysisProject(AmcatModel):
    """
    Explicit many-to-many projects - analyses. Hopefully this can be removed
    when prefetch_related hits the main branch.
    """
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project)
    analysis = models.ForeignKey(Analysis)

    class Meta():
        app_label = 'amcat'
        db_table = "analysis_projects"
        unique_together = ('project', 'analysis')

    def narticles(self, **filter):
        # TODO: this is not very efficient for large projects!
        aids = set(self.project.get_all_article_ids())
        q = AnalysisArticle.objects.filter(article__in=aids, analysis=self.analysis)
        if filter: q = q.filter(**filter)
        return q.count()

class AnalysisSentence(AmcatModel):
    """
    Explicity many-to-many sentence - analysisarticle
    """
    id = models.AutoField(primary_key=True)
    analysis_article = models.ForeignKey(AnalysisArticle, related_name="sentences")
    sentence = models.ForeignKey(Sentence, related_name="analyses")
    
    class Meta():
        app_label = 'amcat'
        db_table = "analysis_sentences"
        unique_together = ('analysis_article', 'sentence')

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

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAnalysis(amcattest.PolicyTestCase):


    def test_store_tokens(self):
        s = amcattest.create_test_analysis_sentence()
        t1 = amcattest.create_tokenvalue(analysis_sentence=s.id)
        s.analysis_article.store_analysis(tokens=[t1])
        aa = AnalysisArticle.objects.get(pk=s.analysis_article.id)
        self.assertEqual(aa.done,  True)
        token, = list(Token.objects.filter(sentence__analysis_article=aa))
        self.assertEqual(token.word.word, t1.word)
        self.assertRaises(aa.store_analysis, tokens=[t1])

    def test_store_triples(self):
        from amcat.models.token import TripleValues
        aa = amcattest.create_test_analysis_article()
        t1 = amcattest.create_tokenvalue(analysis_article=aa)
        t2 = amcattest.create_tokenvalue(analysis_sentence=t1.analysis_sentence, word="x")
        tr = TripleValues(t1.analysis_sentence, parent=t1.position, child=t2.position, relation='su')
        aa.store_analysis(tokens=[t1, t2], triples=[tr])
        aa = AnalysisArticle.objects.get(pk=aa.id)
        triple, = list(Triple.objects.filter(parent__sentence__analysis_article=aa))
        self.assertEqual(triple.parent.word.word, t1.word)
        self.assertEqual(triple.child.word.lemma.lemma, t2.lemma)

