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
from amcat.models.article_preprocessing import ProjectAnalysis
from amcat.tools.toolkit import multidict

def _get_active_project_ids(articles):
    """
    Get all active project ids that the articles are a part of, either directly or
    through articleset membership

    @return: a dictionary of projects per article
    """
    a = Project.objects.filter(articles__in = articles).distinct()

    aids = [a.id for a in articles]
    direct = (Article.objects.filter(pk__in=aids, project__active=True).only("id", "project"))

    result = {a.id : {a.project_id} for a in direct}


    # use many-to-many model to build up query from lowest point
    indirect = (ArticleSetArticle.objects.filter(article__in = aids, articleset__project__active=True)
                .only("article", "articleset__project").select_related("articleset"))
    for asa in indirect:
        result.setdefault(asa.article_id, set()).add(asa.articleset.project_id)

    return result

def _get_analysis_ids(projects):
    """
    Get all analyses that the projects are involved in

    @return: a dictionary of analyses per project
    """
    return multidict((pa.project_id, pa.analysis_id)
                     for pa in ProjectAnalysis.objects.filter(project__in=projects))
    
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestPreprocessing(amcattest.PolicyTestCase):

    def test_get_projects(self):
        p = amcattest.create_test_project()
        a = amcattest.create_test_article(project=p)
        p2 = amcattest.create_test_project()
        a2 = amcattest.create_test_article(project=p2)
        a3 = amcattest.create_test_article(project=p2)
        p3 = amcattest.create_test_project(active=False)
        a4 = amcattest.create_test_article(project=p3)
        with self.checkMaxQueries(n=2):
            self.assertEqual(_get_active_project_ids([a, a2, a3, a4]),
                             {a.id : {p.id}, a2.id : {p2.id}, a3.id : {p2.id}})

        # now let's add a to p2 via a set
        s = amcattest.create_test_set(project=p2)
        s.add(a)
        with self.checkMaxQueries(n=2):
            self.assertEqual(_get_active_project_ids([a, a2, a3, a4]),
                             {a.id : {p.id, p2.id}, a2.id : {p2.id}, a3.id : {p2.id}})
        
        # now let's add a4 (whose project is inactive) to that set
        s.add(a4)
        with self.checkMaxQueries(n=2):
            self.assertEqual(_get_active_project_ids([a, a2, a3, a4]),
                             {a.id : {p.id, p2.id}, a2.id : {p2.id}, a3.id : {p2.id}, a4.id : {p2.id}})
        
        
    def test_get_analysis_ids(self):
        p1, p2 = [amcattest.create_test_project() for _x in range(2)]
        a1, a2, a3 = [amcattest.create_test_analysis() for _x in range(3)]
        with self.checkMaxQueries(n=1):
            self.assertEqual(_get_analysis_ids([p1,p2]), {})

        ProjectAnalysis.objects.create(project=p1, analysis=a1)
        ProjectAnalysis.objects.create(project=p1, analysis=a2)
        ProjectAnalysis.objects.create(project=p2, analysis=a2)
        
        with self.checkMaxQueries(n=1):
            self.assertEqual(_get_analysis_ids([p1,p2]), {p1.id : {a1.id, a2.id}, p2.id : {a2.id}})
            
