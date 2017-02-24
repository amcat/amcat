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
import logging
import collections
import itertools


from django.db import models, transaction, connection

from functools import partial
from django.db.models import sql
from amcat.models.coding.codingschemafield import CodingSchemaField
from amcat.models.coding.coding import CodingValue, Coding
from amcat.tools.djangotoolkit import bulk_insert_returning_ids
from amcat.tools.model import AmcatModel

log = logging.getLogger(__name__)

STATUS_NOTSTARTED, STATUS_INPROGRESS, STATUS_COMPLETE, STATUS_IRRELEVANT = 0, 1, 2, 9

class CodedArticleStatus(AmcatModel):
    id = models.IntegerField(primary_key=True, db_column='status_id')
    label = models.CharField(max_length=50)

    class Meta():
        db_table = 'coded_article_status'
        app_label = 'amcat'

def _to_coding(coded_article, coding):
    """
    Takes a dictionary with keys 'sentence_id', 'start', 'end', and creates
    an (unsaved) Coding object.

    @type codingjob: CodingJob
    @type article: Article
    @type coding: dict
    """
    return Coding(
        coded_article=coded_article, sentence_id=coding.get("sentence_id"),
        start=coding.get("start"), end=coding.get("end")
    )

def _to_codingvalue(coding, codingvalue):
    """
    Takes a dictionary with keys 'codingschemafield_id', 'intval', 'strval' and creates
    an (unsaved) CodingValue object.

    @type coding: Coding
    @type codingvalue: dict
    """
    return CodingValue(
        field_id=codingvalue.get("codingschemafield_id"),
        intval=codingvalue.get("intval"),
        strval=codingvalue.get("strval"),
        coding=coding
    )

def _to_codingvalues(coding, values):
    """
    Takes an iterator with codingvalue dictionaries (see _to_coding) and a coding,
    and returns an iterator with CodingValue's.
    """
    return map(partial(_to_codingvalue, coding), values)


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

    def __unicode__(self):
        return "Article: {self.article}, Codingjob: {self.codingjob}".format(**locals())

    def set_status(self, status):
        """Set the status of this coding, deserialising status as needed"""
        if type(status) == int:
            status = CodedArticleStatus.objects.get(pk=status)
        self.status = status
        self.save()

    def get_codings(self):
        """Returns a generator yielding tuples (coding, [codingvalues])"""
        codings = Coding.objects.filter(coded_article=self)
        values = CodingValue.objects.filter(coding__in=codings)

        values_dict = collections.defaultdict(list)
        for value in values:
            values_dict[value.coding_id].append(value)

        for coding in codings:
            yield (coding, values_dict[coding.id])

    def _replace_codings(self, new_codings):
        # Updating tactic: delete all existing codings and codingvalues, then insert
        # the new ones. This prevents calculating a delta, and confronting the
        # database with (potentially) many update queries.
        CodingValue.objects.filter(coding__coded_article=self).delete()
        Coding.objects.filter(coded_article=self).delete()

        new_coding_objects = list(map(partial(_to_coding, self), new_codings))
        new_coding_objects = bulk_insert_returning_ids(new_coding_objects)

        coding_values = list(itertools.chain.from_iterable(
            _to_codingvalues(co, c["values"]) for c, co in itertools.izip(new_codings, new_coding_objects)
        ))

        return (new_coding_objects, CodingValue.objects.bulk_create(coding_values))

    def replace_codings(self, coding_dicts):
        """
        Creates codings and replace currently existing ones. It takes one parameter
        which has to be an iterator of dictionaries with each dictionary following
        a specific format:

            {
              "sentence_id" : int,
              "start" : int,
              "end" : int,
              "values" : [CodingDict]
            }

        with CodingDict being:

            {
              "codingschemafield_id" : int,
              "intval" : int / NoneType,
              "strval" : str / NoneType
            }

        @raises IntegrityError: codingschemafield_id is None
        @raises ValueError: intval == strval == None
        @raises ValueError: intval != None and strval != None
        @returns: ([Coding], [CodingValue])
        """
        coding_dicts = tuple(coding_dicts)

        values = tuple(itertools.chain.from_iterable(cd["values"] for cd in coding_dicts))
        if any(v.get("intval") == v.get("strval") is None for v in values):
            raise ValueError("intval and strval cannot both be None")

        if any(v.get("intval") is not None and v.get("strval") is not None for v in values):
            raise ValueError("intval and strval cannot both be not None")

        schemas = (self.codingjob.unitschema_id, self.codingjob.articleschema_id)
        fields = CodingSchemaField.objects.filter(codingschema__id__in=schemas)
        field_ids = set(fields.values_list("id", flat=True)) | {None}

        if any(v.get("codingschemafield_id") not in field_ids for v in values):
            raise ValueError("codingschemafield_id must be in codingjob")

        with transaction.atomic():
            return self._replace_codings(coding_dicts)

    class Meta():
        db_table = 'coded_articles'
        app_label = 'amcat'
        unique_together = ("codingjob", "article")


