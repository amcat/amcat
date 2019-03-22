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
Each codingjob has codingschemas for articles and/or sentences.
"""
from collections import namedtuple

from django.db.models.signals import post_save
from django.dispatch import receiver
from amcat.models import CodedArticle, ArticleSet

from amcat.tools.model import AmcatModel
from amcat.tools.table import table3

from amcat.models.user import User

from django.db import models

from amcat.models.user import LITTER_USER_ID
from amcat.models.project import LITTER_PROJECT_ID

import logging;
from amcat.tools.toolkit import splitlist

log = logging.getLogger(__name__)


class CodingJobQuerySet(models.QuerySet):
    def all_in_project(self, project, archived=None):
        jobs = models.Q(project=project)
        if archived is not None:
            jobs &= models.Q(archived=archived)

        if archived is False or archived is None:
            jobs |= models.Q(linked_projects=project)

        return self.filter(jobs)


class CodingJobManager(models.Manager.from_queryset(CodingJobQuerySet)):
    def all_in_project(self, project, archived=None):
        return super().all_in_project(project, archived=archived)


class CodingJob(AmcatModel):
    """
    Model class for table codingjobs. A Coding Job is a container of sets of articles
    assigned to coders in a project with a specified unit and article schema
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='codingjob_id')
    project = models.ForeignKey("amcat.Project")

    name = models.CharField(max_length=100)

    unitschema = models.ForeignKey("amcat.CodingSchema", related_name='codingjobs_unit', null=True, blank=True)
    articleschema = models.ForeignKey("amcat.CodingSchema", related_name='codingjobs_article', null=True, blank=True)

    insertdate = models.DateTimeField(auto_now_add=True)
    insertuser = models.ForeignKey(User, related_name="+")

    coder = models.ForeignKey(User)
    articleset = models.ForeignKey("amcat.ArticleSet", related_name="codingjob_set")

    archived = models.BooleanField(default=False)

    linked_projects = models.ManyToManyField("amcat.Project", related_name="linked_codingjobs")

    objects = CodingJobManager()

    class Meta():

        db_table = 'codingjobs'
        app_label = 'amcat'
        ordering = ('project_id', '-id')

    @property
    def codings(self):
        log.warning("Deprecated: use CodedArticle.codings")
        for coded_article in self.coded_articles.all():
            for coding in coded_article.codings.all():
                yield coding

    def recycle(self):
        """Move this job to the recycle bin"""
        self.project_id = LITTER_PROJECT_ID
        self.coder_id = LITTER_USER_ID
        self.save()

    def get_coded_article(self, article):
        # probably want to use a cached value if it exists?
        return self.coded_articles.get(article=article)


def _create_codingjob_batches(codingjob, article_ids, batch_size):
    name = codingjob.name

    for i, batch in enumerate(splitlist(article_ids, batch_size)):
        codingjob.pk = None
        codingjob.name = "{name} - {i}".format(i=i+1, name=name)
        codingjob.articleset = ArticleSet.create_set(
            project=codingjob.project,
            name=codingjob.name,
            favourite=False,
            articles=batch,
        )

        codingjob.save()
        yield codingjob.pk


def create_codingjob_batches(codingjob, article_ids, batch_size):
    """
    Split article_ids in batches of of 'batch_size', and create a codingjob
    for each batch.

    @param codingjob: Non-saved instance of a codingjob
    @type codingjob: CodingJob
    @type article_ids: [int]
    @type batch_size: int
    """
    codingjob_ids = _create_codingjob_batches(codingjob, article_ids, batch_size)
    return CodingJob.objects.filter(id__in=codingjob_ids)


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
    def get_cell(self, coding):
        return coding.get_value(field=self.field)


