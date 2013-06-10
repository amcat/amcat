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
from __future__ import unicode_literals, print_function, absolute_import

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

def create_new_articleset(name, project):
    """
    Creates new articleset based on name. If articleset exists add postfix number to make articleset name unique.

    @type name: unicode
    @param name: proposed name of new articleset
    @type project: project.Project
    @param project: project attribute of ArticleSet    
    @return: new ArticleSet
    """
    name1 = name
    i = 1
    while ArticleSet.objects.filter(project=project, name=name1).exists():
        i += 1
        name1 = "{name} ({i})".format(**locals())
    return ArticleSet.objects.create(project=project, name=name1)

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
    project = models.ForeignKey("amcat.Project", related_name='articlesets_set')
    articles = models.ManyToManyField(Article, through="amcat.ArticleSetArticle", related_name="articlesets_set")

    provenance = models.TextField(null=True)

    indexed = models.BooleanField(default=None, null=False)
    index_dirty = models.BooleanField(default=True)

    class Meta():
        app_label = 'amcat'
        db_table = 'articlesets'
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
        return self.add_articles(articles)

    def add_articles(self, articles, set_dirty=True):
        """
        Add the given articles to this article set
        @param set_dirty: Set the index_dirty state of this set? (default=True)
        """

        existing = set(aid for (aid,) in self.articles.values_list("id"))
        to_add = set(_articles_to_ids(articles)) - existing

        if not to_add:
            return
        
        ArticleSetArticle.objects.bulk_create(
            [ArticleSetArticle(articleset=self, article_id=artid)
             for artid in to_add]
        )
        if set_dirty:
            self.index_dirty = True
            self.save()
        
    def remove(self, *articles):
        """Remove the given articles from this set"""
        ArticleSetArticle.objects.filter(articleset=self, article__in=articles).delete()
        self.index_dirty = True
        self.save()

    def _get_article_ids(self):
        """
        Get the ids of articles in this set. This is an optimized form of
        'return [a.id for a in self.articles.all()]'
        @return: a set of article ids (integers)
        """
        from django.db import connection
        sql = str(ArticleSet.articles.through.objects.filter(articleset=self).values("article_id").query)
        cursor = connection.cursor()
        cursor.execute(sql)
        result = {aid for (aid,) in cursor.fetchall()}
        cursor.close() # no idea if it's needed, but Martijn told me to do it
        return result

    def _get_article_ids_solr(self, solr):
        """
        Get a list of article ids in this set according to solr. 
        @param solr: The amcatsolr.Solr object to use
        """
        return solr.query_ids("sets:{self.id}".format(**locals()))

    def reset_index(self, full_refresh=False, solr=None):
        """
        Set the index to dirty so it will be refreshed.
        @param full_refresh: if True, delete all existing information from the set
        @param solr: Optional amcatsolr.Solr object to use (e.g. for testing)
        """
        # lazy load to prevent import cycle
        from amcat.tools.amcatsolr import Solr
        if solr is None: solr = Solr()
        if full_refresh:
            solr_ids = self._get_article_ids_solr(solr=solr)
            for i, batch in enumerate(splitlist(solr_ids)):
                solr.delete_articles(batch)
        self.index_dirty=True
        self.save()
    
    def refresh_index(self, solr=None, full_refresh=False):
        """
        Make sure that the SOLR index for this set is up to date
        @param solr: Optional amcatsolr.Solr object to use (e.g. for testing)
        """
        # lazy load to prevent import cycle
        from amcat.tools.amcatsolr import Solr
        if solr is None: solr = Solr()
        log.debug("Getting SOLR ids")
        solr_ids = self._get_article_ids_solr(solr)
        log.debug("Getting DB ids")
        db_ids = set(id for (id,) in self.articles.all().values_list("id")) if self.indexed else set()
        to_remove = solr_ids - db_ids
        to_add = db_ids if full_refresh else  db_ids - solr_ids

        log.warn("Refreshing index, full_refresh={full_refresh}, |solr_ids|={nsolr}, |db_ids|={ndb}, "
                 "|to_add|={nta}, |to_remove|={ntr}"
                  .format(nsolr=len(solr_ids), ndb=len(db_ids), nta=len(to_add), ntr=len(to_remove),**locals()))
        
            
        for i, batch in enumerate(splitlist(to_remove)):
            solr.delete_articles(batch)
            log.debug("Removed batch {i}".format(**locals()))
        for i, batch in enumerate(splitlist(to_add, itemsperbatch=1000)):
            solr.add_articles(batch)
            log.debug("Added batch {i}".format(**locals()))

        self.index_dirty = False
        self.save()
        
    @property
    def index_state(self):
        return (("Indexing in progress" if self.index_dirty else "Fully indexed")
                if self.indexed else "Not indexed")

    def deduplicate(self):
        from amcat.scripts.maintenance import deduplicate
        #TODO: the deduplicate code should go in here!
        deduplicate.DeduplicateScript(articleset=self.id).run()

    def save(self, *args, **kargs):
        new = not self.pk
        super(ArticleSet, self).save(*args, **kargs)
        
        if new:
            # new article set, add as fav to parent project
            # (I run parent first because I guess it needs a pk to add it, but didn't test whether
            #  this is needed...)
            self.project.favourite_articlesets.add(self)
            self.project.save()
        
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
        unique_together = ('article', 'articleset')
    
    
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
        
    def test_add(self):
        """Can we create a set with some articles and retrieve the articles?"""       
        s = amcattest.create_test_set()
        arts = [amcattest.create_test_article() for _x in range(10)]
        s.add_articles(arts[:5])
        self.assertEqual(5, len(s.articles.all()))
        s.add_articles(arts)
        self.assertEqual(len(arts), len(s.articles.all()))
        

        
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
        if amcattest.skip_slow_tests():
            return
        
        from amcat.tools import amcatlogging
        from amcat.tools.amcatsolr import TestSolr, TestDummySolr

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

            # test that remove from index works for larger sets
            s = amcattest.create_test_set(indexed=True)
            arts = [amcattest.create_test_article(medium=a.medium) for i in range(20)]
            s.add(*arts)
            
            s.refresh_index(solr)
            solr_ids = s._get_article_ids_solr(solr)
            self.assertEqual(set(solr_ids), {a.id for a in arts})

            s.remove(arts[0])
            s.remove(arts[-1])
            s.refresh_index(solr)
            solr_ids = s._get_article_ids_solr(solr)
            self.assertEqual(set(solr_ids), {a.id for a in arts[1:-1]})

            

            # test that changing an article's properties can be reindexed 
            arts[1].medium = amcattest.create_test_medium()
            arts[1].save()

            query = "sets:{s.id} AND mediumid:{m}".format(m=arts[1].medium_id, **locals())
            self.assertEqual(set(solr.query_ids(query)), set()) # before refresh
            s.refresh_index(solr, full_refresh=True)
            self.assertEqual(set(solr.query_ids(query)), {arts[1].id}) # after refresh
            
