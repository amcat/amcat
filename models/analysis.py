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
        return self.plugin.get_instance(analysis=self, **options)

    class Meta():
        db_table = 'analyses'
        app_label = 'amcat'

    def __unicode__(self):
        return self.plugin.label if self.plugin else "No plugin available"

class AnalysisQueue(AmcatModel):
    """
    An article on the Analysis Queue needs to be checked for preprocessing
    """

    id = models.AutoField(primary_key=True)
    article = models.ForeignKey(Article)

    class Meta():
        db_table = 'analysis_queue'
        app_label = 'amcat'

    @classmethod
    def narticles_in_queue(cls, project):
        # subqueries for direct and indirect (via set) articles
        direct = Article.objects.filter(project=project).values("id")
        indirect = (ArticleSetArticle.objects.filter(articleset__project=project)
                    .values("article"))
        q = AnalysisQueue.objects.filter(Q(article__in=direct)
                                                | Q(article__in=indirect))
        # add count(distinct) manually - maybe possible through aggregate?
        q = q.extra(select=dict(n="count(distinct article_id)")).values_list("n")
        return q[0][0]


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

    @transaction.commit_on_success
    def store_analysis(self, tokens, triples=None):
        """
        Store the given tokens and triples for this articleanalysis, setting
        it to done=True if stored succesfully.
        """
        if self.done: raise Exception("Cannot store analyses when already done")
        from amcat.nlp.wordcreator import create_triples
        create_triples(tokens, triples)
        self.done = True
        self.save()


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
        aids = set(self.project.get_all_articles())
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

    
# Signal handlers to make sure the article analysis queue is filled
def add_to_queue(*aids):
    for aid in aids:
        AnalysisQueue.objects.create(article_id = aid)

@receiver([post_save, post_delete], Article)
def handle_article(sender, instance, **kargs):
    add_to_queue(instance.id)

@receiver([post_save, post_delete], ArticleSetArticle)
def handle_articlesetarticle(sender, instance, **kargs):
    add_to_queue(instance.article_id)

@receiver([post_save], Project)
def handle_project(sender, instance, **kargs11):
    add_to_queue(*instance.get_all_articles())

@receiver([post_save, post_delete], AnalysisProject)
def handle_projectanalysis(sender, instance, **kargs):
    add_to_queue(*instance.project.get_all_articles())

@receiver([post_save], ArticleSet)
def handle_articleset(sender, instance, **kargs):
    add_to_queue(*(a.id for a in instance.articles.all().only("id")))


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAnalysis(amcattest.PolicyTestCase):

    def test_narticles_in_queue(self):
        # articles added to a project are on the queue
        p = amcattest.create_test_project()
        self.assertEqual(AnalysisQueue.narticles_in_queue(p), 0)
        [amcattest.create_test_article(project=p) for _i in range(10)]
        self.assertEqual(AnalysisQueue.narticles_in_queue(p), 10)

        # articles added to a set in the project are on the queue
        arts = [amcattest.create_test_article() for _i in range(10)]
        s = amcattest.create_test_set(project=p)
        self.assertEqual(AnalysisQueue.narticles_in_queue(p), 10)
        map(s.add, arts)
        self.assertEqual(AnalysisQueue.narticles_in_queue(p), 20)

    def test_article_trigger(self):
        """Is a created or update article in the queue?"""
        self._flush_queue()
        a = amcattest.create_test_article()
        self.assertIn(a.id,  self._all_articles())

        self._flush_queue()
        self.assertNotIn(a.id,  self._all_articles())
        a.headline = "bla bla"
        a.save()
        self.assertIn(a.id,  self._all_articles())


    def test_articleset_triggers(self):
        """Is a article added/removed from a set in the queue?"""

        a = amcattest.create_test_article()
        aset = amcattest.create_test_set()
        self._flush_queue()
        self.assertNotIn(a.id,  self._all_articles())

        aset.add(a)
        self.assertIn(a.id,  self._all_articles())

        self._flush_queue()
        aset.remove(a)
        self.assertIn(a.id, self._all_articles())

        self._flush_queue()
        aid = a.id
        a.delete()
        self.assertIn(aid, self._all_articles())


        b = amcattest.create_test_article()
        aset.add(b)
        self._flush_queue()
        aset.project = amcattest.create_test_project()
        aset.save()
        self.assertIn(b.id, self._all_articles())

    def test_project_triggers(self):
        """Check trigger on project (de)activation and analyses being added/removed from project?"""

        a,b = [amcattest.create_test_article() for _i in range(2)]
        s = amcattest.create_test_set(project=a.project)
        self.assertNotEqual(a.project, b.project)
        s.add(b)

        self._flush_queue()
        a.project.active=True
        a.project.save()
        self.assertIn(a.id, self._all_articles())
        self.assertIn(b.id, self._all_articles())

        self._flush_queue()
        n = amcattest.create_test_analysis()
        AnalysisProject.objects.create(project=a.project, analysis=n)
        self.assertIn(a.id, self._all_articles())
        self.assertIn(b.id, self._all_articles())




    @classmethod
    def _flush_queue(cls):
        """Flush the articles queue"""
        for sa in list(AnalysisQueue.objects.all()): sa.delete()

    @classmethod
    def _all_articles(cls):
        """List all articles on the queue"""
        return set([sa.article_id for sa in AnalysisQueue.objects.all()])

    def test_store_tokens(self):
        s = amcattest.create_test_analysis_sentence()
        t1 = amcattest.create_tokenvalue(analysis_sentence=s)
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

