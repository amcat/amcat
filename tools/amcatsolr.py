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
Function for adding/removing Amcat articles to Solr from the model
"""
from __future__ import unicode_literals, print_function, absolute_import

import datetime, collections, re
import solr
from django.db import connection
from amcat.models.article import Article

from amcat.tools.multithread import distribute_tasks
from amcat.models.article_solr import SolrArticle

import logging
log = logging.getLogger(__name__)

class GMT1(datetime.tzinfo):
    """very basic timezone object, needed for solrpy library.."""
    def utcoffset(self, dt):
        return datetime.timedelta(hours=1)
    def tzname(self, dt):
        return "GMT +1"
    def dst(self, dt):
        return datetime.timedelta(0) 
      
def _clean(text):
    """
    Clean the text for indexing.

    Strip certain control characters to avoid illegal character exception
    """
    #SolrException: HTTP code=400, reason=Illegal character ((CTRL-CHAR, code 20))
    #               at [row,col {unknown-source}]: [3519,150]
    #See also:      http://mail-archives.apache.org/mod_mbox/lucene-solr-user/200901.mbox
    #                     /%3C2c138bed0901040803x4cc07a29i3e022e7f375fc5f@mail.gmail.com%3E
    if not text: return None
    return  re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text)

def _include(article):
    """Should we include this article in the index?"""
    return article.project.active and article.project.indexed

def _ids_to_solr_mutations(article_ids):
    """Given a sequence of ids, return a pair of (article dicts to add, ids to remove)"""
    log.debug(len(article_ids))
    log.debug(article_ids)
    articles = list(Article.objects.filter(pk__in=article_ids)
                    .select_related('project__active', 'project__indexed'))

    log.debug(len(articles))

    # cache set membership
    # TODO: use django querysets instead of sql
    # see development version https://docs.djangoproject.com/en/dev/ref/models/querysets/
    #                                   #django.db.models.query.QuerySet.prefetch_related
    setsDict = collections.defaultdict(list)
    idstr = ",".join(str(a.id) for a in articles if _include(a))
    cursor = connection.cursor()
    if idstr:
        sql = "SELECT articleset_id, article_id FROM articlesets_articles WHERE article_id in (%s)" % idstr
        cursor.execute(sql)
        for setid, articleid in cursor.fetchall():
            setsDict[articleid].append(setid)

    log.debug(len(articles))
    
    to_add, to_remove = [], []
    for a in articles:
        if _include(a):
            to_add.append(dict(id=a.id,
                         headline=_stripChars(a.headline), 
                         body=_stripChars(a.text),
                         byline=_stripChars(a.byline), 
                         section=_stripChars(a.section),
                         projectid=a.project_id,
                         mediumid=a.medium_id,
                         date=a.date.replace(tzinfo=GMT1()),
                         sets=setsDict.get(a.id)))
        else:
            to_remove.append(a.id)
    return to_add, to_remove
            
        
    

def index_articles(article_ids):
    """
    Index the given article ids. Determines which needs to be updated and/or deleted,
    and processes these mutations.
    """
    
    to_add, to_remove = _ids_to_solr_mutations(article_ids)   
    
    log.info("adding/updating %s articles, removing %s" % (len(to_add), len(to_remove)))

    s = solr.SolrConnection('http://localhost:8983/solr')
    if to_add:
        s.add_many(to_add)
    if to_remove:
        log.debug("Removing ids: %s" % to_remove)
        s.delete_many(to_remove)
    s.commit()


def index_articles_from_db(maxn=10000, nthreads=5, batch_size=100, dry_run=False):
    """
    Index articles that are in the 'to-do' table (model SolrArticle)

    Retrieve up to maxn articles, process them in n threads in batches
    of size. After processing, remove the articles from the index.

    @param dry_run: if True, do not actually index the articles
                    (for testing only! the articles will be deleted from the todo table)
    
    @return: the list of indexed article ids.
    """
    
    to_index = [sa.article_id for sa in SolrArticle.objects.all()[:maxn]]
    if to_index:
        log.debug('Will index {n} articles'.format(n=len(to_index)))
        if not dry_run:
            distribute_tasks(to_index, index_articles, nthreads=nthreads,
                             retry_exceptions=True, batch_size=batch_size)
        SolrArticle.objects.filter(article_id__in=to_index).delete()
    return to_index
                 
if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.setup()
    amcatlogging.debug_module()
    index_articles([1,2])

    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest


class TestSolr(amcattest.PolicyTestCase):
    def test_ids2solr(self):
        """Test whether the mutations are retrieved correctly and efficiently"""
        p1 = amcattest.create_test_project(active=True, indexed=True)
        p2 = amcattest.create_test_project(active=True, indexed=False)

        a1 = amcattest.create_test_article(headline="a1", project=p1)
        a2 = amcattest.create_test_article(headline="a2", project=p1)
        a3 = amcattest.create_test_article(headline="a3", project=p2)


        # allow two queries:
        #   1 to get article info (inc. project)
        #   1 to get set membership
        with self.checkMaxQueries(2, "Get mutations"):
            to_add, to_remove = _ids_to_solr_mutations([a1.id, a2.id, a3.id])
        self.assertEqual(to_remove, [a3.id])
        self.assertEqual(len(to_add), 2)
        self.assertEqual(set(a['headline'] for a in to_add), set(["a1","a2"]))
        
        
    
    def test_ids2solr_remove_only(self):
        """Test whether a job with only removals will not give SQL error"""
        p = amcattest.create_test_project(active=False, indexed=True)
        a1 = amcattest.create_test_article(project=p)
        a2 = amcattest.create_test_article(project=p)
        with self.checkMaxQueries(1, "Get mutations"):
            to_add, to_remove = _ids_to_solr_mutations([a1.id, a2.id])

        self.assertEqual(len(to_add), 0)
        self.assertEqual(set(to_remove), set([a1.id, a2.id]))

            
    def test_index_from_db(self):
        """Test whether the correct articles are retrieved from the index"""

        # make sure the 'queue' is empty
        SolrArticle.objects.all().delete()
        self.assertEqual(list(SolrArticle.objects.all()), [])
        indexed = index_articles_from_db(dry_run=True)
        self.assertEqual(indexed, [])

        # add two articles
        p = amcattest.create_test_project(active=True, indexed=True)
        a1 = amcattest.create_test_article(project=p)
        a2 = amcattest.create_test_article(project=p)

        # The triggers won't work on sqlite so add them manually in that case.
        from amcat.tools.dbtoolkit import is_postgres
        if not is_postgres():
            SolrArticle.objects.create(article=a1)
            SolrArticle.objects.create(article=a2)

        indexed = index_articles_from_db(maxn = 1, dry_run=True)
        self.assertEqual(len(indexed), 1)
        indexed += index_articles_from_db(maxn = 1, dry_run=True)
        self.assertEqual(set(indexed), set([a1.id, a2.id]))
        
        # check that the todo table is indeed empty 
        self.assertEqual(list(SolrArticle.objects.all()), [])
        indexed = index_articles_from_db(dry_run=True)
        self.assertEqual(indexed, [])
