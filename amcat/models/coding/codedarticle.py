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
from functools import partial

from django.db import models, transaction, connection, IntegrityError

import logging
from django.db.models import sql
import itertools
from amcat.models.coding.codingschemafield import CodingSchemaField
from amcat.models.coding.coding import CodingValue, Coding
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

        new_coding_objects = map(partial(_to_coding, self), new_codings)

        # Saving each coding is pretty inefficient, but Django doesn't allow retrieving
        # id's when using bulk_create. See Django ticket #19527.
        if connection.vendor == "postgresql":
            query = sql.InsertQuery(Coding)
            query.insert_values(Coding._meta.fields[1:], new_coding_objects)
            raw_sql, params = query.sql_with_params()[0]
            new_coding_objects = Coding.objects.raw("%s %s" % (raw_sql, "RETURNING coding_id"), params)
        else:
            # Do naive O(n) approach
            for coding in new_coding_objects:
                coding.save()

        coding_values = itertools.chain.from_iterable(
            _to_codingvalues(co, c["values"]) for c, co in itertools.izip(new_codings, new_coding_objects)
        )

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
        if any(v.get("intval") == v.get("strval") == None for v in values):
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

    def _get_coding_dict(self, sentence_id=None, field_id=None, intval=None, strval=None, start=None, end=None):
        return {
            "sentence_id" : sentence_id,
            "start" : start,
            "end" : end,
            "values" : [{
                "codingschemafield_id" : field_id,
                "intval" : intval,
                "strval" : strval
            }]
        }

    def test_replace_codings(self):
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields(isarticleschema=True)
        schema2, codebook2, strf2, intf2, codef2 = amcattest.create_test_schema_with_fields(isarticleschema=True)
        codingjob = amcattest.create_test_job(articleschema=schema, narticles=10)

        coded_article = CodedArticle.objects.get(article=codingjob.articleset.articles.all()[0], codingjob=codingjob)
        coded_article.replace_codings([self._get_coding_dict(intval=10, field_id=codef.id)])

        self.assertEqual(1, coded_article.codings.all().count())
        self.assertEqual(1, coded_article.codings.all()[0].values.all().count())
        coding = coded_article.codings.all()[0]
        value = coding.values.all()[0]
        self.assertEqual(coding.sentence, None)
        self.assertEqual(value.strval, None)
        self.assertEqual(value.intval, 10)
        self.assertEqual(value.field, codef)

        # Overwrite previous coding
        coded_article.replace_codings([self._get_coding_dict(intval=11, field_id=intf.id)])
        self.assertEqual(1, coded_article.codings.all().count())
        self.assertEqual(1, coded_article.codings.all()[0].values.all().count())
        coding = coded_article.codings.all()[0]
        value = coding.values.all()[0]
        self.assertEqual(coding.sentence, None)
        self.assertEqual(value.strval, None)
        self.assertEqual(value.intval, 11)
        self.assertEqual(value.field, intf)

        # Try to insert illigal values
        illval1 = self._get_coding_dict(intval=1, strval="a", field_id=intf.id)
        illval2 = self._get_coding_dict(field_id=intf.id)
        illval3 = self._get_coding_dict(intval=1)
        illval4 = self._get_coding_dict(intval=1, field_id=strf2.id)

        self.assertRaises(ValueError, coded_article.replace_codings, [illval1])
        self.assertRaises(ValueError, coded_article.replace_codings, [illval2])
        self.assertRaises(IntegrityError, coded_article.replace_codings, [illval3])
        self.assertRaises(ValueError, coded_article.replace_codings, [illval4])

        # Unspecified values default to None
        val = self._get_coding_dict(intval=1, field_id=intf.id)
        del val["values"][0]["strval"]
        coded_article.replace_codings([val])
        value = coded_article.codings.all()[0].values.all()[0]
        self.assertEqual(value.strval, None)
        self.assertEqual(value.intval, 1)

        val = self._get_coding_dict(strval="a", field_id=intf.id)
        del val["values"][0]["intval"]
        coded_article.replace_codings([val])
        value = coded_article.codings.all()[0].values.all()[0]
        self.assertEqual(value.strval, "a")
        self.assertEqual(value.intval, None)

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

