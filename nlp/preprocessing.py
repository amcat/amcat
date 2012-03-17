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

from amcat.models.article import Article
from amcat.models.project import Project
from amcat.models.articleset import ArticleSetArticle
from amcat.models.article_preprocessing import ProjectAnalysis, ArticleAnalysis
from amcat.tools.toolkit import multidict, wrapped

def _get_active_project_ids(articles):
    """
    Get all active project ids that the articles are a part of, either directly or
    through articleset membership

    @return: a sequence of article id : project id pairs
    """
    aids = [a.id for a in articles]
    # direct project membership
    for a in Article.objects.filter(pk__in=aids, project__active=True).only("id", "project"):
        yield a.id, a.project_id

    # indirect membership via sets
    # use many-to-many model to build up query from lowest point
    for asa in (ArticleSetArticle.objects
                .filter(article__in = aids, articleset__project__active=True)
                .only("article", "articleset__project").select_related("articleset")):
        yield asa.article_id, asa.articleset.project_id

def _get_analysis_ids(projects):
    """
    Get all analyses that the projects are involved in

    @return: a sequence of project id : analysis id pairs
    """
    for pa in ProjectAnalysis.objects.filter(project__in=projects):
        yield pa.project_id, pa.analysis_id

def _get_analyses_per_article(articles):
    """
    For each article, determine which analyses should be processed by what analyses
    based on direct and indirect (via articleset) project membership
    
    @return: a sequence of article id : analysis id pairs.
    """
    projects_per_article = list(_get_active_project_ids(articles))
    
    all_projects = {p for (a,p) in projects_per_article}
    analyses_per_project = multidict(_get_analysis_ids(all_projects))

    for article, project in projects_per_article:
        for analysis in analyses_per_project.get(project, set()):
            yield article, analysis
          
def _get_articles_preprocessing_actions(articles):
    """
    For the given articles, determine which analyses need to be performed
    and which analyses have already been performed or which analyses need
    to be deleted.

    @return: a tuple of (additions, deletions), where
            additions: a list of (article, analysis) paris
            deletions: a list of ArticleAnalysis ids
    """
    required = set(_get_analyses_per_article(articles))
    deletions = []
    for aa in ArticleAnalysis.objects.filter(article__in=articles):
        try:
            # remove this analysis from the required analyses
            required.remove((aa.article_id, aa.analysis_id))
        except KeyError:
            # it wasn't on the required analyses, so add to deletions
            deletions.append(aa.id)

    return required, deletions
        
            
        
    
            
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestPreprocessing(amcattest.PolicyTestCase):

    
    def test_articles_preprocessing_actions(self):
        p1, p2 = [amcattest.create_test_project() for x in range(2)]
        a1, a2, a3 = [amcattest.create_test_article(project=p) for p in [p1, p2, p2]]
        articles = {a1, a2, a3}
        
        # baseline: no articles need any analysis, and no deletions are needed
        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, deletions = _get_articles_preprocessing_actions(articles)
            self.assertEqual(set(additions), set())
            self.assertEqual(set(deletions), set())

        # add some analyses to the active projects
        n1, n2, n3 = [amcattest.create_test_analysis() for _x in range(3)]
        ProjectAnalysis.objects.create(project=p1, analysis=n1)
        ProjectAnalysis.objects.create(project=p1, analysis=n2)
        ProjectAnalysis.objects.create(project=p2, analysis=n2)
            
        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, deletions = _get_articles_preprocessing_actions(articles)
            self.assertEqual(multidict(additions), {1: {1,2}, 2:{2}, 3:{2}})
            self.assertEqual(set(deletions), set())

        # add some existing analyses
        ArticleAnalysis.objects.create(article=a1, analysis=n1)
        ArticleAnalysis.objects.create(article=a2, analysis=n1)
        ArticleAnalysis.objects.create(article=a3, analysis=n2)
        
        with self.checkMaxQueries(n=4): # 3 for needed, 1 for existing
            additions, deletions = _get_articles_preprocessing_actions(articles)
            self.assertEqual(multidict(additions), {1: {2}, 2:{2}})
        todel = set()
        for aaid in deletions:
            aa = ArticleAnalysis.objects.get(pk=aaid)
            todel.add((aa.article_id, aa.analysis_id))
            self.assertEqual(set(todel), {(2, 1)})

    def test_analyses_per_article(self):
        p1, p2, p3 = [amcattest.create_test_project(active=x<2) for x in range(3)]
        a1 = amcattest.create_test_article(project=p1)
        a2 = amcattest.create_test_article(project=p2)
        a3 = amcattest.create_test_article(project=p2)
        a4 = amcattest.create_test_article(project=p3)
        articles = {a1, a2, a3, a4}
        
        # baseline: no articles have any analysis
        with self.checkMaxQueries(n=3): # 2 for projects/article, 1 for analyses/project
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {})

        # let's add some analyses to the active projects
        n1, n2, n3 = [amcattest.create_test_analysis() for _x in range(3)]
        ProjectAnalysis.objects.create(project=p1, analysis=n1)
        ProjectAnalysis.objects.create(project=p1, analysis=n2)
        ProjectAnalysis.objects.create(project=p2, analysis=n2)
        ProjectAnalysis.objects.create(project=p2, analysis=n3)
        with self.checkMaxQueries(n=3):
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {a1.id : {n1.id, n2.id},
                                       a2.id : {n2.id, n3.id},
                                       a3.id : {n2.id, n3.id}})
            
        # adding an analysis to an inactive project has no effect
        ProjectAnalysis.objects.create(project=p3, analysis=n3)
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
        ProjectAnalysis.objects.create(project=p3, analysis=n2)
        with self.checkMaxQueries(n=3):
            outcome = multidict(_get_analyses_per_article(articles))
            self.assertEqual(outcome, {a1.id : {n1.id, n2.id},
                                       a2.id : {n1.id, n2.id, n3.id},
                                       a3.id : {n2.id, n3.id},
                                       a4.id : {n1.id, n2.id}})
        
    
    def test_get_projects(self):
        p = amcattest.create_test_project()
        a = amcattest.create_test_article(project=p)
        p2 = amcattest.create_test_project()
        a2 = amcattest.create_test_article(project=p2)
        a3 = amcattest.create_test_article(project=p2)
        p3 = amcattest.create_test_project(active=False)
        a4 = amcattest.create_test_article(project=p3)
        with self.checkMaxQueries(n=2):
            outcome = multidict(_get_active_project_ids([a, a2, a3, a4]))
            self.assertEqual(outcome, {a.id : {p.id}, a2.id : {p2.id}, a3.id : {p2.id}})

        # now let's add a to p2 via a set
        s = amcattest.create_test_set(project=p2)
        s.add(a)
        with self.checkMaxQueries(n=2):
            outcome = multidict(_get_active_project_ids([a, a2, a3, a4]))
            self.assertEqual(outcome, {a.id : {p.id, p2.id}, a2.id : {p2.id}, a3.id : {p2.id}})
        
        # now let's add a4 (whose project is inactive) to that set
        s.add(a4)
        with self.checkMaxQueries(n=2):
            outcome = multidict(_get_active_project_ids([a, a2, a3, a4]))
            self.assertEqual(outcome, {a.id : {p.id, p2.id}, a2.id : {p2.id},
                                       a3.id : {p2.id}, a4.id : {p2.id}})

            
        
    def test_get_analysis_ids(self):
        p1, p2 = [amcattest.create_test_project() for _x in range(2)]
        a1, a2, a3 = [amcattest.create_test_analysis() for _x in range(3)]
        with self.checkMaxQueries(n=1):
            outcome = multidict(_get_analysis_ids([p1,p2]))
            self.assertEqual(outcome, {})

        ProjectAnalysis.objects.create(project=p1, analysis=a1)
        ProjectAnalysis.objects.create(project=p1, analysis=a2)
        ProjectAnalysis.objects.create(project=p2, analysis=a2)
        
        with self.checkMaxQueries(n=1):
            outcome = multidict(_get_analysis_ids([p1,p2]))
            self.assertEqual(outcome, {p1.id : {a1.id, a2.id}, p2.id : {a2.id}})
            
