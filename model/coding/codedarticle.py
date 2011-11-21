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

A CodedArticle represents an article in a codingjob set and provides a convenient
way to access article and sentence codings. CodedArticles have no direct
representation in the database.
"""

import logging; log = logging.getLogger(__name__)

from amcat.tools.idlabel import Identity
from amcat.model.coding.coding import Coding

class CodedArticle(Identity):
    """Convenience class to represent an article in a codingjobset
    and expose the article and sentence codings
    
    @param codingjobset_or_coding: Either a job set, or an coding
    @param article: the coded article, or None if an coding was given as first argument
    """
    def __init__(self, codingjobset_or_coding, article=None):
        if article is None:
            codingjobset = codingjobset_or_coding.codingjobset
            article = codingjobset_or_coding.article
        else:
            codingjobset = codingjobset_or_coding
        super(CodedArticle, self).__init__(codingjobset.id, article.id)
        self.codingjobset = codingjobset
        self.article = article

    @property
    def coding(self):
        """Get the  article coding for this coded article"""
        result = self.codingjobset.codings.filter(article=self.article, sentence__isnull=True)
        if result: return result[0]

    def get_or_create_coding(self):
        """Get or create the article coding for this coded article"""
        a = self.coding
        if a is None:
            a = Coding.objects.create(codingjobset=self.codingjobset, article=self.article)
        return a

    def create_sentence_coding(self, sentence):
        """Create a new sentence coding on the given sentence"""
        return Coding.objects.create(codingjobset=self.codingjobset, article=self.article,
                                 sentence=sentence)
    
    @property
    def sentence_codings(self):
        """Get the sentence codings for this coded article"""
        return self.codingjobset.codings.filter(article=self.article, sentence__isnull=False)

    
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodedArticle(amcattest.PolicyTestCase):
    
    def test_codedarticle(self):
        """Test whether CodedArticle coding retrieval works"""
        a = amcattest.create_test_coding()
        s = amcattest.create_test_sentence()
        a2 = amcattest.create_test_coding(sentence=s, codingjobset=a.codingjobset)
        a3 = amcattest.create_test_coding(sentence=s, codingjobset=a.codingjobset)
        ca = CodedArticle(a)

        self.assertEqual(set(ca.sentence_codings), {a2, a3})
        self.assertEqual(ca.coding, a)

    def test_create_codings(self):
        """Does get/create coding work?"""
        
        a = amcattest.create_test_coding()
        ca = CodedArticle(a)
        self.assertEqual(ca.coding, a)
        self.assertEqual(ca.get_or_create_coding(), a)

        codingids = {a.id for a in Coding.objects.all()}
        ca = CodedArticle(ca.codingjobset, amcattest.create_test_article())
        self.assertIsNone(ca.coding)
        a2 = ca.get_or_create_coding()
        self.assertNotIn(a2.id, codingids)
        self.assertEqual(ca.coding, a2)
        self.assertEqual(ca.get_or_create_coding(), a2)
        
        
        
        
        
