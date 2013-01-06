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
Business logic for article preprocessing

See http://code.google.com/p/amcat/wiki/Preprocessing
"""
from amcat.models import Sentence

from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle
from amcat.models.analysis import AnalysisProject, AnalysisArticle, AnalysisSentence, Analysis
from amcat.nlp import sbd 
from amcat.tools.toolkit import multidict

import logging; log = logging.getLogger(__name__)

def _get_active_project_ids(articleids):
    """
    Get all active project ids that the articles are a part of, either directly or
    through articleset membership

    @return: a sequence of article id : project id pairs
    """
    # direct project membership
    for a in Article.objects.filter(pk__in=articleids, project__active=True).only("id", "project"):
        yield a.id, a.project_id

    # indirect membership via sets
    # use many-to-many model to build up query from lowest point
    for asa in (ArticleSetArticle.objects
                .filter(article__in = articleids, articleset__project__active=True)
                .only("article", "articleset__project").select_related("articleset")):
        yield asa.article_id, asa.articleset.project_id

def _get_analysis_ids(projects):
    """
    Get all analyses that the projects are involved in

    @return: a sequence of project id : analysis id pairs
    """
    for pa in AnalysisProject.objects.filter(project__in=projects):
        yield pa.project_id, pa.analysis_id

def _get_analyses_per_article(articleids):
    """
    For each article, determine which analyses should be processed by what analyses
    based on direct and indirect (via articleset) project membership

    @return: a sequence of article id : analysis id pairs.
    """
    projects_per_article = list(_get_active_project_ids(articleids))

    all_projects = {p for (a,p) in projects_per_article}
    analyses_per_project = multidict(_get_analysis_ids(all_projects))

    for article, project in projects_per_article:
        for analysis in analyses_per_project.get(project, set()):
            yield article, analysis

def _get_articles_preprocessing_actions(articleids):
    """
    For the given articles, determine which analyses need to be performed
    and which analyses have already been performed or which analyses need
    to be deleted.

    @return: a tuple of (additions, deletions), where
            additions: a list of (article, analysis) paris
            deletions: a list of ArticleAnalysis ids
            undeletions: a list of ArticleAnalysis ids
    """
    required = set(_get_analyses_per_article(articleids))
    deletions, undeletions, restarts = [], [], []

    for aa in AnalysisArticle.objects.filter(article__id__in=articleids):
        try:
            # remove this analysis from the required analyses
            required.remove((aa.article_id, aa.analysis_id))
        except KeyError:
            # it wasn't on the required analyses, so add to deletions
            deletions.append(aa.id)
        else:
            # it was on the required analyses, undelete if needed
            if aa.delete:
                undeletions.append(aa.id)

            # and restart analysis
            if aa.started and aa.done:
                restarts.append(aa.id)

    return required, restarts, deletions, undeletions

def split_article(article):
    """Split the given article and return the sentence objects"""
    sentences = sbd.create_sentences(article)
    for sentence in sentences:
        sentence.save()
    return sentences

def create_sentences_articles(analysis_articles):
    """
    Create AnalysisSentence objects for the given articles where needed
    """
    anids = set(aa.analysis_id for aa in analysis_articles)
    sentence_analyses = set(pk for (pk,) in Analysis.objects.filter(pk__in=anids, sentences=True).values_list("pk"))
    for aa in analysis_articles:
        if aa.analysis_id in sentence_analyses:
            create_sentences(aa)


def create_sentences(analysis_article):
    """
    Create AnalysisSentence objects for this article
    """
    sentences = list(Sentence.objects.filter(article=analysis_article.article_id))
    if not sentences:
        sentences = split_article(analysis_article.article)
    for sentence in sentences:
        AnalysisSentence.objects.create(analysis_article=analysis_article, sentence=sentence)

def set_preprocessing_actions(articleids):
    """
    For the given articles, make sure that the actual state in the articles_analyses
    table matches the desired state from project membership and projects_analyses.
    """
    required, restarts, deletions, undeletions = _get_articles_preprocessing_actions(articleids)

    if required:
        aas = [AnalysisArticle.objects.create(article_id=artid, analysis_id=anid)
               for artid, anid in required]
        create_sentences_articles(aas)
    if deletions:
        AnalysisArticle.objects.filter(id__in=deletions).update(delete=True)
    if undeletions:
        AnalysisArticle.objects.filter(id__in=undeletions).update(delete=False)
    if restarts:
        AnalysisArticle.objects.filter(id__in=restarts).update(started=False, done=False)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestPreprocessing(amcattest.PolicyTestCase):

    def _get_analyses(self, articles):
        return {(aa.article_id, aa.analysis_id) : aa.delete
                for aa in AnalysisArticle.objects.filter(article__in=articles)}

    def todo_test_set_preprocessing_actions(self):
        p1, p2 = [amcattest.create_test_project() for _x in range(2)]
        a1, a2 = [amcattest.create_test_article(project=p) for p in [p1, p2]]
        n1 = amcattest.create_test_analysis()
        articles = {a1.id, a2.id}

        with self.checkMaxQueries(n=2): #  2 sentences
            split_article(a1)
            split_article(a2)


        # baseline: no analyses
        with self.checkMaxQueries(n=4): # 4 for querying, 0 for mutations
            set_preprocessing_actions(articles)
        self.assertEqual(self._get_analyses(articles), {})

        # test addition: activate analysis 1 on p1
        AnalysisProject.objects.create(project=p1, analysis=n1)
        with self.checkMaxQueries(n=8):
            # 4 for querying, 1 for mutations,
            # 2 for checking sentence, 1 for creating sentences
            set_preprocessing_actions(articles)
        self.assertEqual(self._get_analyses(articles), {(a1.id, n1.id) : False})
        s, = AnalysisSentence.objects.filter(analysis_article__article=a1)
        self.assertEqual(s.analysis_article.analysis_id, n1.id)

        # test another addition: activate analysis 1 on p2
        AnalysisProject.objects.create(project=p2, analysis=n1)
        with self.checkMaxQueries(n=9): # 4 for querying, 1 for mutations
            set_preprocessing_actions(articles)
        self.assertEqual(self._get_analyses(articles), {(a1.id, n1.id) : False,
                                                        (a2.id, n1.id) : False})

        # test deletions: deactivate project 1
        p1.active = False
        p1.save()
        with self.checkMaxQueries(n=5): # 4 for querying, 1 for mutations
            set_preprocessing_actions(articles)
        self.assertEqual(self._get_analyses(articles), {(a1.id, n1.id) : True,
                                                        (a2.id, n1.id) : False})

        # test re-activation: reactivate project 1
        p1.active = True
        p1.save()
        with self.checkMaxQueries(n=5): # 4 for querying, 1 for mutations
            set_preprocessing_actions(articles)
        self.assertEqual(self._get_analyses(articles), {(a1.id, n1.id) : False,
                                                        (a2.id, n1.id) : False})

    def test_articles_preprocessing_restarts(self):
        p1 = amcattest.create_test_project()
        a1 = amcattest.create_test_article(project=p1)
        n1 = amcattest.create_test_analysis()

        # Activate analysis
        AnalysisProject.objects.create(project=p1, analysis=n1)
        AnalysisArticle.objects.create(article=a1, analysis=n1, started=True, done=True)

        with self.checkMaxQueries(n=4):
            additions, restarts, deletions, undeletions = _get_articles_preprocessing_actions((a1.id,))

            self.assertEqual(set(additions), set())
            self.assertEqual(set(deletions), set())
            self.assertEqual(set(undeletions), set())
            self.assertEqual(len(restarts), 1)

    def test_articles_preprocessing_actions(self):
        p1, p2 = [amcattest.create_test_project() for x in range(2)]
        a1, a2, a3 = [amcattest.create_test_article(project=p) for p in [p1, p2, p2]]
        articles = {a1.id, a2.id, a3.id}

        # baseline: no articles need any analysis, and no deletions are needed
        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, restarts, deletions, undeletions = _get_articles_preprocessing_actions(articles)
            self.assertEqual(set(additions), set())
            self.assertEqual(set(deletions), set())
            self.assertEqual(set(undeletions), set())
            self.assertEqual(set(restarts), set())

        # add some analyses to the active projects
        n1, n2, n3 = [amcattest.create_test_analysis() for _x in range(3)]
        AnalysisProject.objects.create(project=p1, analysis=n1)
        AnalysisProject.objects.create(project=p1, analysis=n2)
        AnalysisProject.objects.create(project=p2, analysis=n2)

        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, restarts, deletions, undeletions = _get_articles_preprocessing_actions(articles)
            self.assertEqual(multidict(additions), {a1.id: {n1.id,n2.id}, a2.id:{n2.id}, a3.id:{n2.id}})
            self.assertEqual(set(deletions), set())
            self.assertEqual(set(undeletions), set())
            self.assertEqual(set(restarts), set())

        # add some existing analyses
        AnalysisArticle.objects.create(article=a1, analysis=n1)
        AnalysisArticle.objects.create(article=a2, analysis=n1)
        AnalysisArticle.objects.create(article=a3, analysis=n2)

        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, restarts, deletions, undeletions = _get_articles_preprocessing_actions(articles)
            self.assertEqual(multidict(additions), {a1.id: {n2.id}, a2.id:{n2.id}})
        todel = set()
        for aaid in deletions:
            aa = AnalysisArticle.objects.get(pk=aaid)
            todel.add((aa.article_id, aa.analysis_id))
        self.assertEqual(set(todel), {(a2.id, n1.id)})
        self.assertEqual(set(undeletions), set())

    def test_articles_preprocessing_reactivate(self):
        """Are deleted analyses undeleted when they are reactivated?"""
        p1 = amcattest.create_test_project()
        a1 = amcattest.create_test_article(project=p1)
        n1 = amcattest.create_test_analysis()
        AnalysisProject.objects.create(project=p1, analysis=n1)

        # baseline: check that required=actual gives a no-op
        aa = AnalysisArticle.objects.create(article=a1, analysis=n1)
        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, restarts, deletions, undeletions = _get_articles_preprocessing_actions([a1.id])
            self.assertEqual(multidict(additions), {})
            self.assertEqual(list(deletions), [])
            self.assertEqual(set(undeletions), set())
            self.assertEqual(set(restarts), set())

        # now set the aa to delete and see if it is reactivated
        aa.delete=True
        aa.save()
        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, restarts, deletions, undeletions = _get_articles_preprocessing_actions([a1.id])
            self.assertEqual(multidict(additions), {})
            self.assertEqual(list(deletions), [])
            self.assertEqual(set(undeletions), {aa.id})
            self.assertEqual(set(restarts), set())

    def todo_test_analyses_per_article(self):
        p1, p2, p3 = [amcattest.create_test_project(active=x<2) for x in range(3)]
        a1 = amcattest.create_test_article(project=p1)
        a2 = amcattest.create_test_article(project=p2)
        a3 = amcattest.create_test_article(project=p2)
        a4 = amcattest.create_test_article(project=p3)
        articles = {a1.id, a2.id, a3.id, a4.id}

        # baseline: no articles have any analysis
        with self.checkMaxQueries(n=3): # 2 for projects/article, 1 for analyses/project
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {})

        # let's add some analyses to the active projects
        n1, n2, n3 = [amcattest.create_test_analysis() for _x in range(3)]
        AnalysisProject.objects.create(project=p1, analysis=n1)
        AnalysisProject.objects.create(project=p1, analysis=n2)
        AnalysisProject.objects.create(project=p2, analysis=n2)
        AnalysisProject.objects.create(project=p2, analysis=n3)
        with self.checkMaxQueries(n=3):
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {a1.id : {n1.id, n2.id},
                                       a2.id : {n2.id, n3.id},
                                       a3.id : {n2.id, n3.id}})

        # adding an analysis to an inactive project has no effect
        AnalysisProject.objects.create(project=p3, analysis=n3)
        with self.checkMaxQueries(n=3):
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {a1.id : {n1.id, n2.id},
                                       a2.id : {n2.id, n3.id},
                                       a3.id : {n2.id, n3.id}})

        # adding an article to a project via a set does have effect
        s1 = amcattest.create_test_set(project=p1)
        s2 = amcattest.create_test_set(project=p2)
        s1.add(a4)
        s1.add(a2)
        AnalysisProject.objects.create(project=p3, analysis=n2)
        with self.checkMaxQueries(n=3):
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {a1.id : {n1.id, n2.id},
                                       a2.id : {n1.id, n2.id, n3.id},
                                       a3.id : {n2.id, n3.id},
                                       a4.id : {n1.id, n2.id}})


    def todo_test_get_projects(self):
        p = amcattest.create_test_project()
        a = amcattest.create_test_article(project=p)
        p2 = amcattest.create_test_project()
        a2 = amcattest.create_test_article(project=p2)
        a3 = amcattest.create_test_article(project=p2)
        p3 = amcattest.create_test_project(active=False)
        a4 = amcattest.create_test_article(project=p3)
        articleids = {a.id, a2.id, a3.id, a4.id}
        with self.checkMaxQueries(n=2):
            outcome = multidict(_get_active_project_ids(articleids))
            self.assertEqual(outcome, {a.id : {p.id}, a2.id : {p2.id}, a3.id : {p2.id}})

        # now let's add a to p2 via a set
        s = amcattest.create_test_set(project=p2)
        s.add(a)
        with self.checkMaxQueries(n=2):
            outcome = multidict(_get_active_project_ids(articleids))
            self.assertEqual(outcome, {a.id : {p.id, p2.id}, a2.id : {p2.id}, a3.id : {p2.id}})

        # now let's add a4 (whose project is inactive) to that set
        s.add(a4)
        with self.checkMaxQueries(n=2):
            outcome = multidict(_get_active_project_ids(articleids))
            self.assertEqual(outcome, {a.id : {p.id, p2.id}, a2.id : {p2.id},
                                       a3.id : {p2.id}, a4.id : {p2.id}})



    def test_get_analysis_ids(self):
        p1, p2 = [amcattest.create_test_project() for _x in range(2)]
        a1, a2, a3 = [amcattest.create_test_analysis() for _x in range(3)]
        with self.checkMaxQueries(n=1):
            outcome = multidict(_get_analysis_ids([p1,p2]))
            self.assertEqual(outcome, {})

        AnalysisProject.objects.create(project=p1, analysis=a1)
        AnalysisProject.objects.create(project=p1, analysis=a2)
        AnalysisProject.objects.create(project=p2, analysis=a2)

        with self.checkMaxQueries(n=1):
            outcome = multidict(_get_analysis_ids([p1,p2]))
            self.assertEqual(outcome, {p1.id : {a1.id, a2.id}, p2.id : {a2.id}})

    def test_split_article(self):
        a = amcattest.create_test_article(headline="dit is een kop", text="Een eerste zin. En een tweede")
        split_article(a)
        sents = list(a.sentences.all())
        self.assertEqual(len(sents), 3)

    def test_create_sentences_article(self):
        a = amcattest.create_test_article(headline="dit is een kop", text="Een eerste zin. En een tweede")
        aa = amcattest.create_test_analysis_article(article=a)
        create_sentences(aa)
        sents = list(a.sentences.all())
        self.assertEqual(len(sents), 3)
        self.assertRaises(Exception, split_article, a)
        # does a second analysis on the same article use the same sentences?
        aa2 = amcattest.create_test_analysis_article(article=a)
        create_sentences(aa2)
        sents2 = set(s.sentence for s in a.sentences.all())
        self.assertEqual(sents2, set(s.sentence for s in sents))
