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
Model module containing the Article class representing documents in the
articles database table
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.tools.model import AmcatModel

from amcat.model.project import Project
from amcat.model.authorisation import Role
from amcat.model.medium import Medium

from django.db import models

import logging; log = logging.getLogger(__name__)

import re

WORD_RE = re.compile('[{L}{N}]+') # {L} --> All (unicode) letters
                                  # {N} --> All numbers

def word_len(txt):
    """Count words in `txt`

    @type txt: str or unicode"""
    if not txt: return 0 # Safe handling of txt=None
    return len(re.sub(WORD_RE, ' ', txt).split())

class Article(AmcatModel):
    """
    Class representing a newspaper article
    """
    id = models.AutoField(primary_key=True, db_column="article_id")

    date = models.DateTimeField(db_index=True)
    section = models.CharField(blank=True, null=True, max_length=500)
    pagenr = models.IntegerField(blank=True, null=True)
    headline = models.TextField(db_index=True)
    byline = models.TextField(blank=True, null=True, max_length=500)
    length = models.IntegerField()
    metastring = models.TextField(null=True)
    url = models.URLField(null=True, blank=True, db_index=True, max_length=1000)
    externalid = models.IntegerField(blank=True, null=True)
    author = models.CharField(max_length=100, blank=True, null=True)

    #sets = models.ManyToManyField("amcat.Set", db_table="sets_articles")
    
    text = models.TextField()

    parent = models.ForeignKey("self", null=True, db_column="parent_article_id",
                               db_index=True, blank=True)
    project = models.ForeignKey(Project, db_index=True)
    medium = models.ForeignKey(Medium, db_index=True)

    def __unicode__(self):
        return self.headline

    class Meta():
        db_table = 'articles'
        app_label = 'amcat'

    @property
    def children(self):
        """Return a sequence of all child articles (eg reactions to a post)"""
        return Article.objects.filter(parent=self)

    def save(self, *args, **kwargs):
        if self.length is None:
            self.length = word_len(self.text)

        super(Article, self).save(*args, **kwargs)


    def words(self):
        "@return: a generator yielding all words in all sentences"
        for sentence in self.sentences:
            for word in sentence.words:
                yield word

    def getSentence(self, parnr, sentnr):
        "@return: a Sentence object with the given paragraph and sentence number"
        for s in self.sentences:
            if s.parnr == parnr and s.sentnr == sentnr:
                return s

    ## Auth ##
    def can_read(self, user):
        if user.is_superuser:
            return True

        # Check default role on project
        read_meta = Role.objects.get(label='metareader', projectlevel=True)
        if self.project.guest_role.id >= read_meta.id:
            return True

        # Check users role on project
        if user.projectrole_set.filter(project__set__article=self, role__id__gt=read_meta.id):
            return True

        return False


    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestArticle(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create an article object?"""
        a = amcattest.create_test_article()
        self.assertIsNotNone(a)

    def test_unicode(self):
        """Test unicode headlines"""
        for offset in range(1, 10000, 1000):
            s = "".join(unichr(offset + c) for c in range(1, 1000, 100))
            a = amcattest.create_test_article(headline=s)
            self.assertIsInstance(a.headline, unicode)
            self.assertEqual(a.headline, s)
