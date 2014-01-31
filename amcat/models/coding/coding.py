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
Model module containing Codings

A coding is a hook for the coding values on a specific article linked
to a specific coding job set.
"""

from __future__ import print_function
from django.db import transaction

from amcat.tools.toolkit import deprecated

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.models.coding.codingschemafield import CodingSchemaField
from amcat.models.sentence import Sentence

import logging
log = logging.getLogger(__name__)

def create_coding(codingjob, article, **kwargs):
    from amcat.models.coding.codedarticle import CodedArticle
    coded_article, _ = CodedArticle.objects.get_or_create(codingjob=codingjob, article=article)
    return Coding.objects.create(coded_article=coded_article, **kwargs)

def coded_article_property(prop):
    """Returns property object fetches the given property on CodedArticle instaed of Coding."""
    def get_property(self):
        log.warning("Getting `{prop}` from Coding deprecated. Use CodedArticle.")
        return getattr(self.coded_article, prop)

    def set_property(self, value):
        log.warning("Setting `{prop}` on Coding deprecated. Use CodedArticle.")
        setattr(self.coded_article, prop, value)
        self._coded_article_changed = True

    return property(get_property, set_property)

class Coding(AmcatModel):
    """
    Model class for codings. Codings provide the link between a Coding Job 
    and actual Coding Values. 
    """
    id = models.AutoField(primary_key=True, db_column='coding_id')

    coded_article = models.ForeignKey("amcat.CodedArticle", related_name="codings")
    sentence = models.ForeignKey(Sentence, null=True)

    # These values allow subsentence codings. Better names would be from
    # and to, but from is a reserved keyword in both Python and SQL (?).
    start = models.SmallIntegerField(null=True)
    end = models.SmallIntegerField(null=True)

    def __init__(self, *args, **kwargs):
        super(Coding, self).__init__(*args, **kwargs)
        self._coded_article_changed = False

    class Meta():
        db_table = 'codings'
        app_label = 'amcat'

    @property
    def schema(self):
        """Get the coding schema that this coding is based on"""
        if self.sentence_id is None:
            return self.coded_article.codingjob.articleschema
        return self.coded_article.codingjob.unitschema

    def get_values(self):
        """Return a sequence of field, (deserialized) value pairs"""
        return [(v.field, v.value) for v in (
                self.values.order_by('field__fieldnr')
                .select_related("field__fieldtype", "value__strval", "value__intval"))]

    def get_value_object(self, field):
        """Return the Value object correspoding to this field"""
        for v in self.values.all():
            if v.field_id == field.id:
                return v
        raise CodingValue.DoesNotExist()

    def get_value(self, field):
        """Return serialised value correspoding to this field"""
        try:
            return self.get_value_object(field).get_serialised_value(field=field)
        except CodingValue.DoesNotExist:
            pass

    def _get_coding_value(self, field, value):
        if isinstance(value, int):
            return CodingValue(field=field, coding=self, intval=value)
        return CodingValue(field=field, coding=self, strval=value)

    @transaction.atomic
    def update_values(self, values_dict):
        self.values.all().delete()
        CodingValue.objects.bulk_create(self._get_coding_value(f, v) for f, v in values_dict.items())

    def save(self, *args, **kwargs):
        # This is deprecated behaviour intended to
        if self._coded_article_changed:
            self.coded_article.save(*args, **kwargs)
            self._coded_article_changed = False
        return super(Coding, self).save(*args, **kwargs)

    ##############################################################
    #                         DEPRECATED                         #
    ##############################################################
    status = coded_article_property("status")
    status_id = coded_article_property("status_id")
    comments = coded_article_property("comments")
    article = coded_article_property("article")
    article_id = coded_article_property("article_id")
    codingjob = coded_article_property("codingjob")
    codingjob_id = coded_article_property("codingjob_id")

    @deprecated
    def set_status(self, status):
        return self.coded_article.set_status(status)



class CodingValue(AmcatModel):
    """
    Model class for coding values. 
    """
    
    id = models.AutoField(primary_key=True, db_column='codingvalue_id')

    coding = models.ForeignKey(Coding, related_name='values')
    field = models.ForeignKey(CodingSchemaField)

    strval = models.CharField(blank=True, null=True, max_length=1000)
    intval = models.IntegerField(null=True)

    def save(self, *args, **kargs):
        #Enforce constraint (strval IS NOT NULL) OR (intval IS NOT NULL)
        if self.strval is None and self.intval is None:
            raise ValueError("codingvalue.strval and .intval cannot both be None")
        if self.strval is not None and self.intval is not None:
            raise ValueError("codingvalue.strval and .intval cannot both be not None")
        super(CodingValue, self).save(*args, **kargs)

    @property
    def serialised_value(self):
        return self.get_serialised_value()
    
    def get_serialised_value(self, field=None):
        """Get the 'serialised' (raw) value for this codingvalue
        @param field: for optimization, specify the field if it is known
        """
        if field is None:
            field = next(f for f in self.coding.schema.fields.all() if f.id == self.field_id)
        stype = field.serialiser.deserialised_type
        if stype == unicode: return self.strval
        return self.intval

    @property
    def value(self):
        """Get the 'deserialised' (object) value for this codingvalue"""
        return self.field.serialiser.deserialise(self.serialised_value)

    class Meta():
        db_table = 'codings_values'
        app_label = 'amcat'
        unique_together = ("coding", "field")

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCoding(amcattest.AmCATTestCase):

    def setUp(self):
        """Set up a simple coding schema with fields to use for testing"""
        super(TestCoding, self).setUp()

        self.schema, self.codebook,  self.strfield, self.intfield, self.codefield = (
            amcattest.create_test_schema_with_fields())

        self.c = amcattest.create_test_code(label="CODED")
        self.c2 = amcattest.create_test_code(label="CODE2")
        self.codebook.add_code(self.c)
        self.codebook.add_code(self.c2)
        
        self.job = amcattest.create_test_job(unitschema=self.schema, articleschema=self.schema)
        
    def test_create(self):
        """Can we create an coding?"""
        schema2 = amcattest.create_test_schema()
        j = amcattest.create_test_job(unitschema=self.schema, articleschema=schema2)
        a = amcattest.create_test_coding(codingjob=j)
        self.assertIsNotNone(a)
        self.assertIn(a.article, j.articleset.articles.all())
        self.assertEqual(a.schema, schema2)
        a2 = amcattest.create_test_coding(codingjob=j,
                                              sentence=amcattest.create_test_sentence())
        self.assertEqual(a2.schema, self.schema)

    def test_update_values(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields(codebook=codebook)
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=7)
        articles = list(job.articleset.articles.all())

        coding = amcattest.create_test_coding(codingjob=job, article=articles[0])
        self.assertEqual(0, coding.values.count())
        coding.update_values({strf:"bla", intf:1, codef:codes["A1b"].id})
        self.assertEqual(3, coding.values.count())
        self.assertTrue(strf in dict(coding.get_values()))
        self.assertTrue(intf in dict(coding.get_values()))
        self.assertTrue(codef in dict(coding.get_values()))
        self.assertEqual(1, dict(coding.get_values())[intf])

        # Does update_values delete values not present in dict?
        coding.update_values({strf:"blas"})
        self.assertEqual(1, coding.values.count())
        self.assertTrue(strf in dict(coding.get_values()))
        self.assertEqual("blas", dict(coding.get_values())[strf])



    def test_create_value(self):
        """Can we create an coding value?"""
        a = amcattest.create_test_coding(codingjob=self.job)
        v = CodingValue.objects.create(coding=a, field=self.strfield, strval="abc")
        v2 = CodingValue.objects.create(coding=a, field=self.intfield, intval=1)
        v3 = CodingValue.objects.create(coding=a, field=self.codefield, intval=self.c.id)
        
        self.assertIn(v, a.values.all())
        self.assertEqual(v.value, "abc")
        self.assertEqual(v2.value, 1)
        self.assertEqual(v3.value, self.c)

        self.assertEqual(list(a.get_values()),
                         [(self.strfield, "abc"), (self.intfield, 1), (self.codefield, self.c)])

        # null values for both value fields
        self.assertRaises(ValueError, CodingValue.objects.create,
                          coding=amcattest.create_test_coding(codingjob=self.job),
                          field=self.strfield)

