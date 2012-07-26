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
Module for the CodedArticle convenience class

A CodedArticle represents an article in a codingjob and provides a convenient
way to access article and sentence codings. CodedArticles have no direct
representation in the database.
"""

import logging; log = logging.getLogger(__name__)

from amcat.tools.idlabel import Identity
from amcat.models.coding.coding import Coding

import collections

def _cache_codings(coded_articles, articles=None):
    """
    Cache codings for given coded_articles    
    """
    if not coded_articles: return

    codingjob = coded_articles.values()[0].codingjob
    todo = [a.id for a in articles or codingjob.articleset.articles.all()]

    codings = Coding.objects.select_related("status").filter(
        codingjob=codingjob, sentence__isnull=True,
        article__in=articles
    )

    # Set cache for found codings
    for coding in codings:
        ca = coded_articles.get(coding.article_id)
        ca._set_coding_cache(coding)

        todo.remove(coding.article_id)

    # Set cache to empty (None) for codings not found
    for article in todo:
        coded_articles.get(article.id)._set_coding_cache(None)

def _cache_sentences(coded_articles, articles=None):
    """
    Cache sentences for given coded_articles
    """
    if not coded_articles: return

    codingjob = coded_articles.values()[0].codingjob
    todo = collections.defaultdict(list)

    codings = Coding.objects.filter(
        article__in=articles or codingjob.articleset.articles.all(),
        sentence__isnull=False,
        codingjob=codingjob
    ).order_by('sentence__parnr', 'sentence__sentnr')

    # Group by codingjob
    for coding in codings:
        todo[coding.article_id].append(coding)

    # Set cache. Empty caches are automatically set due to the use of
    # defaultdict
    for article_id, coded_article in coded_articles.items():
        coded_article._set_sentence_codings_cache(todo[article_id])

def bulk_create_codedarticles(
        codingjob, cache_sentences=True, cache_coding=True,
        articles=None, select_related_codings=tuple()
    ):
    """
    Create CodedArticles in batch and cache certain properties.

    @param codingjob: codingjob to create codedarticles for
    @type codingjob: amcat.models.CodingJob

    @param cache_sentences: cache CodedArticle().sentence_codings
    @type cache_sentences: boolean

    @param cache_coding: cache CodedArticle().coding
    @type cache_coding: boolean

    @type articles: iterable or None
    @param articles: which articles to use. If left None, all articles
                     of the given codingjob are used.
    """
    articles = codingjob.articleset.articles.all() if articles is None else articles
    coded_articles = dict([(art.id, CodedArticle(codingjob, art)) for art in articles])

    # Cache codings with one query
    if cache_coding is True:
        _cache_codings(coded_articles, articles)

    # Cache sentence codings
    if cache_sentences:
        _cache_sentences(coded_articles, articles)

    return coded_articles.values()

class CodedArticle(Identity):
    """Convenience class to represent an article in a codingjob
    and expose the article and sentence codings
    
    @param codingjob_or_coding: Either a job or an coding
    @param article: the coded article, or None if an coding was given as first argument
    """
    def __init__(self, codingjob_or_coding, article=None):
        if article is None:
            self.codingjob = codingjob_or_coding.codingjob
            self.article = codingjob_or_coding.article
        else:
            self.codingjob = codingjob_or_coding
            self.article = article

        super(CodedArticle, self).__init__(self.codingjob.id, self.article.id)

    def _set_coding_cache(self, coding):
        self._coding = coding

    def _set_sentence_codings_cache(self, sentence_codings):
        self._sentence_codings = sentence_codings

    @property
    def coding(self):
        """Get the  article coding for this coded article"""
        # Try to return cache
        try:
            return self._coding
        except AttributeError:
            pass

        # Fetch coding and fill cache
        try:
            self._coding = self.codingjob.codings.get(
                article=self.article, sentence__isnull=True
            )
        except Coding.DoesNotExist:
            self._coding = None

        return self._coding

    def get_or_create_coding(self):
        """Get or create the article coding for this coded article"""
        a = self.coding
        if a is None:
            a = Coding.objects.create(codingjob=self.codingjob, article=self.article)
        return a

    def create_sentence_coding(self, sentence):
        """Create a new sentence coding on the given sentence"""
        return Coding.objects.create(codingjob=self.codingjob, article=self.article,
                                 sentence=sentence)
    
    @property
    def sentence_codings(self):
        """Get the sentence codings for this coded article"""
        try:
            return self._sentence_codings
        except AttributeError:
            pass

        self._sentence_codings = self.codingjob.codings.filter(
            article=self.article, sentence__isnull=False
        ).order_by('sentence__parnr', 'sentence__sentnr')

        return self._sentence_codings
    
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodedArticle(amcattest.PolicyTestCase):
    
    def test_codedarticle(self):
        """Test whether CodedArticle coding retrieval works"""
        a = amcattest.create_test_coding()
        s = amcattest.create_test_sentence()
        a2 = amcattest.create_test_coding(sentence=s, codingjob=a.codingjob)
        a3 = amcattest.create_test_coding(sentence=s, codingjob=a.codingjob)
        ca = CodedArticle(a)

        self.assertEqual(set(ca.sentence_codings), set([a2, a3]))
        self.assertEqual(ca.coding, a)

    def test_create_codings(self):
        """Does get/create coding work?"""
        
        a = amcattest.create_test_coding()
        ca = CodedArticle(a)
        self.assertEqual(ca.coding, a)
        self.assertEqual(ca.get_or_create_coding(), a)

        codingids = set(a.id for a in Coding.objects.all())
        ca = CodedArticle(ca.codingjob, amcattest.create_test_article())
        self.assertIsNone(ca.coding)
        a2 = ca.get_or_create_coding()
        self.assertNotIn(a2.id, codingids)
        self.assertEqual(ca.coding, a2)
        self.assertEqual(ca.get_or_create_coding(), a2)
        
        
        
        
        
