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
Model module for Article Sets. A Set is a generic collection of articles,
either created manually or as a result of importing articles or assigning
coding jobs.
"""

from amcat.tools.toolkit import splitlist
from amcat.tools.model import AmcatModel
from amcat.tools.djangotoolkit import get_or_create
from amcat.models.article import Article

from django.db import models

import logging
log = logging.getLogger(__name__)

def get_or_create_articleset(name, project):
    """
    Finds an articleset based on its name. If it does not exists, it creates
    one and returns that one instead.

    @type name: unicode
    @param name: name attribute of ArticleSet
    @type project: project.Project
    @param project: project attribute of ArticleSet
    @return: ArticleSet object or None if name is None
    """
    return get_or_create(ArticleSet, name=name, project=project) if name else None

def _articles_to_ids(articles):
    """
    Convert given articles to article ids.

    @param articles: articles to convert
    @type articles: iterable with each type(object) in (int, Article)
    """
    for art in articles:
        yield art if type(art) is int else art.id

class ArticleSet(AmcatModel):
    """
    Model for the sets table. A set is part of a project and contains articles.
    It can also be seen as a 'tag' for articles.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='articleset_id')

    name = models.CharField(max_length=200)
    project = models.ForeignKey("amcat.Project", related_name='articlesets')
    articles = models.ManyToManyField(Article, through="amcat.ArticleSetArticle", related_name="articlesets")

    codingjobset = models.BooleanField(default=False)
    batch = models.BooleanField(default=False)
    
    provenance = models.TextField(null=True)

    indexed = models.BooleanField(default=None, null=False)
    index_dirty = models.BooleanField(default=True)

    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
        unique_together = ('name', 'project')
        ordering = ['name']

    def __init__(self, *args, **kargs):
        super(ArticleSet, self).__init__(*args, **kargs)
        # default value for indexed from project.
        # Check for project_id to prevent error on bare instantiation, e.g. for a form
        # TODO should we override create/save instead?
        if self.indexed is None and self.project_id is not None:
            self.indexed = self.project.index_default
        
    def add(self, *articles):
        """Add the given articles to this article set"""
        return self.add_articles(article)

    def add_articles(self, articles, set_dirty=True):
        """
        Add the given articles to this article set
        @param set_dirty: Set the index_dirty state of this set? (default=True)
        """
        
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid)\
             for artid in _articles_to_ids(articles)]
        )
        if set_dirty:
            self.index_dirty = True
            self.save()
        
    def remove(self, *articles):
        """Remove the given articles from this set"""
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()
        self.index_dirty = True
        self.save()

    def refresh_index(self, solr=None):
        """
        Make sure that the SOLR index for this set is up to date
        @param solr: Optional amcatsolr.Solr object to use (e.g. for testing)
        """
        # lazy load to prevent import cycle
        from amcat.tools.amcatsolr import Solr


        if solr is None: solr = Solr()
        solr_ids = self._get_article_ids_solr(solr)
        if self.indexed:
            db_ids = set(id for (id,) in self.articles.all().values_list("id"))
        else:
            db_ids = set()
        log.debug("Refreshing index, |solr_ids|={nsolr}, |db_ids|={ndb}"
                  .format(nsolr=len(solr_ids), ndb=len(db_ids)))
        for i, batch in enumerate(splitlist(db_ids - solr_ids, itemsperbatch=1000)):
            solr.add_articles(batch)
            log.debug("Added batch {i}".format(**locals()))
        for i, batch in enumerate(splitlist(solr_ids - db_ids)):
            solr.delete_articles(solr_ids - db_ids)
            log.debug("Removed batch {i}".format(**locals()))

        self.index_dirty = False
        self.save()
        
    def _get_article_ids_solr(self, solr):
        """
        Which article ids are in this set according to solr?
        @param solr: Optional amcatsolr.Solr object to use (e.g. for testing)
        """
        return set(solr.query_ids("sets: {self.id}".format(**locals())))

    @property
    def index_state(self):
        return (("Indexing in progress" if self.index_dirty else "Fully indexed")
                if self.indexed else "Not indexed")

        
class ArticleSetArticle(AmcatModel):
    """
    ManyToMany table for article sets. An explicit model allows more prefeting in
    django queries and doesn't cost anything

    WVA: I believe this is no longer needed with the new prefetch_related, so
         we might be able to refactor this class away?
    """
    id = models.AutoField(primary_key=True, db_column='id')
    articleset = models.ForeignKey(ArticleSet)
    article = models.ForeignKey(Article)

    class Meta():
        app_label = 'amcat'
        db_table="articlesets_articles"
    
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestArticleSet(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create a set with some articles and retrieve the articles?"""       
        s = amcattest.create_test_set()
        i = 7
        for _x in range(i):
            s.add(amcattest.create_test_article())
        self.assertEqual(i, len(s.articles.all()))
    
        
    def test_dirty(self):
        """Is the dirty flag set correctly?"""
        from amcat.tools.amcatsolr import TestSolr, TestDummySolr

        p = amcattest.create_test_project(index_default=True)
        s = amcattest.create_test_set(project=p)
        self.assertEqual(s.indexed, True)
        self.assertEqual(s.index_dirty, True)
        s.index_dirty=False
        s.save()
        s.add(amcattest.create_test_article())
        self.assertEqual(s.index_dirty, True)
        s.refresh_index(TestDummySolr())
        self.assertEqual(s.index_dirty, False)

    def test_refresh_index(self):
        """Are added/removed articles added/removed from the index?"""
        from amcat.tools import amcatlogging
        from amcat.tools.amcatsolr import TestSolr, TestDummySolr

        amcatlogging.info_module("amcat.tools.amcatsolr")
        with TestSolr() as solr:
            s = amcattest.create_test_set(indexed=True)
            a = amcattest.create_test_article()
            
            s.add(a)
            self.assertEqual(set(), s._get_article_ids_solr(solr))
            s.refresh_index(solr)
            self.assertEqual({a.id}, s._get_article_ids_solr(solr))

            s.remove(a)
            self.assertEqual({a.id}, s._get_article_ids_solr(solr))
            s.refresh_index(solr)
            self.assertEqual(set(), s._get_article_ids_solr(solr))

            # test that if not set.indexed, it is not added to solr
            s = amcattest.create_test_set(indexed=False)
            s.add(a)
            s.refresh_index(solr)
            self.assertEqual(set(), s._get_article_ids_solr(solr))
