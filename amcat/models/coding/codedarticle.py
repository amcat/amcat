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
import collections

from django.db import models

import logging
from amcat.tools.model import AmcatModel

log = logging.getLogger(__name__)

STATUS_NOTSTARTED, STATUS_INPROGRESS, STATUS_COMPLETE, STATUS_IRRELEVANT = 0, 1, 2, 9

class CodedArticleStatus(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='status_id')
    label = models.CharField(max_length=50)

    class Meta():
        db_table = 'coded_article_status'
        app_label = 'amcat'

class CodedArticle(models.Model):
    """
    A CodedArticle is an article in a context of two other objects: a codingjob and an
    article. It exist for every (codingjob, article) in {codingjobs} X {codingjobarticles}
    and is created when creating a codingjob (see `create_coded_articles` in codingjob.py).

    Each coded article contains codings (1:N) and each coding contains codingvalues (1:N).
    """
    comments = models.TextField(blank=True, null=True)
    status = models.ForeignKey(CodedArticleStatus, default=STATUS_NOTSTARTED)
    article = models.ForeignKey("amcat.Article", related_name="coded_articles")
    codingjob = models.ForeignKey("amcat.CodingJob", related_name="coded_articles")

    def set_status(self, status):
        """Set the status of this coding, deserialising status as needed"""
        if type(status) == int:
            status = CodedArticleStatus.objects.get(pk=status)
        self.status = status
        self.save()

    def get_codings(self):
        """Returns a generator yielding tuples (coding, [codingvalues])"""
        from amcat.models import Coding, CodingValue

        codings = Coding.objects.filter(coded_article=self)
        values = CodingValue.objects.filter(coding__in=codings)

        values_dict = collections.defaultdict(list)
        for value in values:
            values_dict[value.coding_id].append(value)

        for coding in codings:
            yield (coding, values_dict[coding.id])

    class Meta():
        db_table = 'coded_articles'
        app_label = 'amcat'
        unique_together = ("codingjob", "article")

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodedArticle(amcattest.AmCATTestCase):
    def test_comments(self):
        """Can we set and read comments?"""
        from amcat.models import Coding
        a = amcattest.create_test_coding()
        self.assertIsNone(a.comments)

        for offset in range(4563, 20000, 1000):
            s = "".join(unichr(offset + c) for c in range(12, 1000, 100))
            a.comments = s
            a.save()
            a = Coding.objects.get(pk=a.id)
            self.assertEqual(a.comments, s)

class TestCodedArticleStatus(amcattest.AmCATTestCase):
    def test_status(self):
        """Is initial status 0? Can we set it?"""
        a = amcattest.create_test_coding()
        self.assertEqual(a.status.id, 0)
        self.assertEqual(a.status, CodedArticleStatus.objects.get(pk=STATUS_NOTSTARTED))
        a.set_status(STATUS_INPROGRESS)
        self.assertEqual(a.status, CodedArticleStatus.objects.get(pk=1))
        a.set_status(STATUS_COMPLETE)
        self.assertEqual(a.status, CodedArticleStatus.objects.get(pk=2))
        a.set_status(STATUS_IRRELEVANT)
        self.assertEqual(a.status, CodedArticleStatus.objects.get(pk=9))
        a.set_status(STATUS_NOTSTARTED)
        self.assertEqual(a.status, CodedArticleStatus.objects.get(pk=0))

