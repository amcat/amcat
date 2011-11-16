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
way to access article and sentence annotations. CodedArticles have no direct
representation in the database.
"""

import logging; log = logging.getLogger(__name__)

from amcat.tools.idlabel import Identity
from amcat.model.coding.annotation import Annotation

class CodedArticle(Identity):
    """Convenience class to represent an article in a codingjobset
    and expose the article and sentence annotations
    
    @param codingjobset_or_annotation: Either a job set, or an annotation
    @param article: the coded article, or None if an annotation was given as first argument
    """
    def __init__(self, codingjobset_or_annotation, article=None):
        if article is None:
            codingjobset = codingjobset_or_annotation.codingjobset
            article = codingjobset_or_annotation.article
        else:
            codingjobset = codingjobset_or_annotation
        super(CodedArticle, self).__init__(codingjobset.id, article.id)
        self.codingjobset = codingjobset
        self.article = article

    @property
    def annotation(self):
        """Get the  article annotation for this coded article"""
        result = self.codingjobset.annotations.filter(article=self.article, sentence__isnull=True)
        if result: return result[0]

    def get_or_create_annotation(self):
        """Get or create the article annotation for this coded article"""
        a = self.annotation
        if a is None:
            a = Annotation.objects.create(codingjobset=self.codingjobset, article=self.article)
        return a

    def create_sentence_annotation(self, sentence):
        return Annotation.objects.create(codingjobset=self.codingjobset, article=self.article,
                                 sentence=sentence)
    
    @property
    def sentence_annotations(self):
        """Get the sentence annotations for this coded article"""
        return self.codingjobset.annotations.filter(article=self.article, sentence__isnull=False)

    
    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodedArticle(amcattest.PolicyTestCase):
    
    def test_codedarticle(self):
        """Test whether CodedArticle annotation retrieval works"""
        a = amcattest.create_test_annotation()
        s = amcattest.create_test_sentence()
        a2 = amcattest.create_test_annotation(sentence=s, codingjobset=a.codingjobset)
        a3 = amcattest.create_test_annotation(sentence=s, codingjobset=a.codingjobset)
        ca = CodedArticle(a)

        self.assertEqual(set(ca.sentence_annotations), {a2, a3})
        self.assertEqual(ca.annotation, a)

    def test_create_annotations(self):
        """Does get/create annotation work?"""
        
        a = amcattest.create_test_annotation()
        ca = CodedArticle(a)
        self.assertEqual(ca.annotation, a)
        self.assertEqual(ca.get_or_create_annotation(), a)

        annotationids = {a.id for a in Annotation.objects.all()}
        ca = CodedArticle(ca.codingjobset, amcattest.create_test_article())
        self.assertIsNone(ca.annotation)
        a2 = ca.get_or_create_annotation()
        self.assertNotIn(a2.id, annotationids)
        self.assertEqual(ca.annotation, a2)
        self.assertEqual(ca.get_or_create_annotation(), a2)
        
        
        
        
        
