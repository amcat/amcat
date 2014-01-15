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
Model module containing Codingjobs

Coding Jobs are sets of articles assigned to users for manual coding.
Each coding job has codingschemas for articles and/or sentences.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from amcat.models import CodedArticle

from amcat.tools.model import AmcatModel
from amcat.tools.table import table3

from amcat.models.coding.codingschema import CodingSchema
from amcat.models.user import User
from amcat.models.articleset import ArticleSet

from django.db import models

import logging; log = logging.getLogger(__name__)
            
class CodingJob(AmcatModel):
    """
    Model class for table codingjobs. A Coding Job is a container of sets of articles
    assigned to coders in a project with a specified unit and article schema
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='codingjob_id')
    project = models.ForeignKey("amcat.Project")

    name = models.CharField(max_length=100)

    unitschema = models.ForeignKey(CodingSchema, related_name='codingjobs_unit')
    articleschema = models.ForeignKey(CodingSchema, related_name='codingjobs_article')

    insertdate = models.DateTimeField(auto_now_add=True)
    insertuser = models.ForeignKey(User, related_name="+")

    coder = models.ForeignKey(User)
    articleset = models.ForeignKey(ArticleSet, related_name="codingjob_set")
    
    class Meta():
        db_table = 'codingjobs'
        app_label = 'amcat'
        ordering = ('project', '-id')

    @property
    def codings(self):
        log.warning("Deprecated: use CodedArticle.codings")
        for coded_article in self.coded_articles.all():
            for coding in coded_article.codings.all():
                yield coding

@receiver(post_save, sender=CodingJob)
def create_coded_articles(sender, instance=None, created=None, **kwargs):
    """
    For each article in the codingjobs articleset, a CodedArticle needs to be
    present. This signal receiver creates the necessary objects after a
    codingjob is created.
    """
    if not created: return

    # Singal gets called multiple times, workaround:
    if CodedArticle.objects.filter(codingjob=instance).exists(): return

    aids = instance.articleset.articles.all().values_list("id", flat=True)
    coded_articles = (CodedArticle(codingjob=instance, article_id=aid) for aid in aids)
    CodedArticle.objects.bulk_create(coded_articles)

class SchemaFieldColumn(table3.ObjectColumn):
    def __init__(self, field):
        super(SchemaFieldColumn, self).__init__(field.label)
        self.field = field
    def getCell(self, coding):
        return coding.get_value(field=self.field)
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodingJob(amcattest.AmCATTestCase):
    def test_create(self):
        """Can we create a coding job with articles?"""
        from amcat.models.project import Project
        p = amcattest.create_test_project()
        j = amcattest.create_test_job(project=p)
        self.assertIsNotNone(j)
        self.assertEqual(j.project, Project.objects.get(pk=p.id))
        j.articleset.add(amcattest.create_test_article())
        j.articleset.add(amcattest.create_test_article())
        j.articleset.add(amcattest.create_test_article())
        self.assertEqual(1+3, len(j.articleset.articles.all()))

    def test_post_create(self):
        job = amcattest.create_test_job(10)
        self.assertEqual(CodedArticle.objects.filter(codingjob=job).count(), 10)

