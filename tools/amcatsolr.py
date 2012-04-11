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

import re
import datetime
import logging
log = logging.getLogger(__name__)

import solr

from amcat.models.articleset import ArticleSetArticle
from amcat.tools import toolkit



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
    text = re.sub('[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text)
    return text

def create_article_dicts(articles):
    sets = toolkit.multidict((aa.article_id, aa.articleset_id)
                              for aa in ArticleSetArticle.objects.filter(article__in=articles))
    for a in articles:
        yield dict(id=a.id,
                   headline=_clean(a.headline),
                   body=_clean(a.text),
                   byline=_clean(a.byline),
                   section=_clean(a.section),
                   projectid=a.project_id,
                   mediumid=a.medium_id,
                   date=a.date.replace(tzinfo=GMT1()),
                   sets=sets.get(a.id))

def index_articles(articles):
    dicts = list(create_article_dicts(articles))
    if dicts:
        log.debug("Adding %i articles to solr" % len(dicts))
        s = solr.SolrConnection(b'http://localhost:8983/solr')
        s.add_many(dicts)
        s.commit()

def delete_articles(articles):
    aids = [a.id for a in articles]
    if aids:
        log.debug("Removing %i articles from solr" % len(aids))
        s = solr.SolrConnection(b'http://localhost:8983/solr')
        s.delete_many(aids)
        s.commit()

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAmcatSolr(amcattest.PolicyTestCase):

    def test_clean(self):
        """Test whether cleaning works correctly"""
        i = "\x00A\x01B\x08C\x0BD\x0CE\x0EF\x1DG\x1FH"
        o = " A B C D E F G H"
        self.assertEqual(_clean(i), o)

    def test_create_article_dicts(self):
        """Test whether article dicts are created correctly"""
        from amcat.models.article import Article
        s1,s2 = [amcattest.create_test_set() for _x in range(2)]
        p  = amcattest.create_test_project()
        m = amcattest.create_test_medium()
        a1 = amcattest.create_test_article(headline="bla \x1d blo", text="test",
                                           project=p, medium=m)

        a2 = amcattest.create_test_article(headline="blabla", text="t\xe9st!",
                                           byline="\u0904\u0905 test", project=p, medium=m)
        s1.add(a1)
        s2.add(a1)
        s2.add(a2)

        # force getting to make db rountrip and deserialize date
        ad1, ad2 = list(create_article_dicts(Article.objects.filter(pk__in=[a1.id, a2.id])))
        for k,v in dict(id=a1.id, headline="bla   blo", body="test", byline=None,
                        section=None, projectid=p.id, mediumid=m.id,
                        sets=set([s1.id, s2.id])).items():
            self.assertEqual(ad1[k], v, "Article 1 %s %r!=%r" % (k, ad1[k], v))

        for k,v in dict(id=a2.id, headline="blabla", body="t\xe9st!", byline="\u0904\u0905 test",
                        section=None, projectid=p.id, mediumid=m.id,
                        sets=set([s2.id])).items():
            self.assertEqual(ad2[k], v, "Article 2 %s %r!=%r" % (k, ad2[k], v))
