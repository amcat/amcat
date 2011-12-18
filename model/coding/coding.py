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

import logging; log = logging.getLogger(__name__)

from django.db import models

from amcat.tools.caching import cached, invalidates
from amcat.tools.model import AmcatModel
from amcat.model.coding.codingjob import CodingJob
from amcat.model.coding.codingschemafield import CodingSchemaField
from amcat.model.article import Article
from amcat.model.sentence import Sentence


class CodingStatus(AmcatModel):
    """
    Helder class for coding status
    """

    id = models.IntegerField(primary_key=True, db_column='status_id')
    label = models.CharField(max_length=50)

    def __unicode__(self):
        return self.label
    
    class Meta():
        db_table = 'codings_status'
        app_label = 'amcat'


STATUS_NOTSTARTED, STATUS_INPROGRESS, STATUS_COMPLETE, STATUS_IRRELEVANT = 0, 1, 2, 9
        
class Coding(AmcatModel):
    """
    Model class for codings. Codings provide the link between a Coding Job 
    and actual Coding Values. 
    """

    id = models.AutoField(primary_key=True, db_column='coding_id')
    
    codingjob = models.ForeignKey(CodingJob, related_name="codings")
    article = models.ForeignKey(Article)
    sentence = models.ForeignKey(Sentence, null=True)

    comments = models.TextField(blank=True, null=True)
    status = models.ForeignKey(CodingStatus, default=0)
    
    class Meta():
        db_table = 'codings'
        app_label = 'amcat'

    @property
    def schema(self):
        """Get the coding schema that this coding is based on"""
        if self.sentence is None:
            return self.codingjob.articleschema
        else:
            return self.codingjob.unitschema

    @cached
    def get_values(self):
        """Return a sequence of field, (deserialized) value pairs"""
        return [(v.field, v.value) for v in (
                self.values.order_by('field__fieldnr')
                .select_related("field__fieldtype", "value__strval", "value__intval"))]

    @invalidates
    def update_values(self, values):
        """Update the current values

        @param values: mapping of field to serialised value.
        Fields that are not included in the mapping, or whose value are set to
        None, will be removed from the values
        """
        current = {v.field : v for v in self.values.all()}

        for field, value in values.items():
            if field in current:
                if value is None:
                    # explicit delete for value None
                    current[field].delete()
                else: 
                    current[field].update_value(value)
                # This field from current was encountered, so don't delete below                    
                del current[field]
            else: 
                self.set_value(field, value)
        #delete remaining values in current
        for value in current.values():
            # implicit delete by not listing in values mapping 
            value.delete()


    def set_status(self, status):
        """Set the status of this coding, deserialising status as needed"""
        if type(status) == int: status = CodingStatus.objects.get(pk=status)
        self.status = status

    @invalidates
    def set_value(self, field, value):
        """Create a new coding value on this coding

        @param field: the coding schema field
        @param value: the deserialized value
        """
        a = CodingValue(coding=self, field=field)
        a.update_value(value)
        a.save()
        
        
class CodingValue(AmcatModel):
    """
    Model class for coding values. 
    """
    
    id = models.AutoField(primary_key=True, db_column='codingvalue_id')

    coding = models.ForeignKey(Coding, related_name='values')
    field = models.ForeignKey(CodingSchemaField)

    strval = models.CharField(blank=True, null=True, max_length=500)
    intval = models.IntegerField(null=True)

    def save(self, *args, **kargs):
        #Enforce constraint field.schema == coding.schema
        if self.field.codingschema != self.coding.schema:
            raise ValueError("Field schema {0!r} and coding schema {1!r} don't match"
                             .format(self.field.codingschema, self.coding.schema))
        #Enforce constraint (strval IS NOT NULL) OR (intval IS NOT NULL)
        if self.strval is None and self.intval is None:
            raise ValueError("codingvalue.strval and .intval cannot both be None")
        super(CodingValue, self).save(*args, **kargs)

    
    @property
    def serialised_value(self):
        """Get the 'serialised' (raw) value for this codingvalue"""
        stype = self.field.serialiser.deserialised_type
        if stype == str: return self.strval
        return self.intval

    @property
    def value(self):
        """Get the 'deserialised' (object) value for this codingvalue"""
        return self.field.serialiser.deserialise(self.serialised_value)

    def update_value(self, value):
        """Update to the given (deserialised) value by serialising and
        updating strval or intval, as appropriate"""
        serval = self.field.serialiser.serialise(value)
        stype = self.field.serialiser.deserialised_type
        if stype == str: self.strval = serval
        else: self.intval = serval
        self.save()

    class Meta():
        db_table = 'codings_values'
        app_label = 'amcat'
        unique_together = ("coding", "field")

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest


def _valuestr(coding):
    """Dense representation of coding values for quick comparison"""
    return ";".join("{0.label}:{1!r}".format(*fv) for (fv) in
                    sorted(coding.get_values(), key=lambda fv:fv[0].label))
        

class TestCoding(amcattest.PolicyTestCase):

    def setUp(self):
        """Set up a simple coding schema with fields to use for testing"""
        super(TestCoding, self).setUp()
        from amcat.model.coding.codingschemafield import CodingSchemaFieldType
        strfieldtype = CodingSchemaFieldType.objects.get(pk=1)
        intfieldtype = CodingSchemaFieldType.objects.get(pk=2)
        codefieldtype = CodingSchemaFieldType.objects.get(pk=5)


        self.codebook = amcattest.create_test_codebook()
        self.c = amcattest.create_test_code(label="CODED")
        self.c2 = amcattest.create_test_code(label="CODE2")
        self.codebook.add_code(self.c)
        self.codebook.add_code(self.c2)

        self.schema = amcattest.create_test_schema()
        create = CodingSchemaField.objects.create
        self.strfield = create(codingschema=self.schema, fieldnr=1, label="text",
                               fieldtype=strfieldtype)
        self.intfield = create(codingschema=self.schema, fieldnr=2, label="number",
                               fieldtype=intfieldtype)
        self.codefield = create(codingschema=self.schema, fieldnr=3, label="code",
                                fieldtype=codefieldtype, codebook=self.codebook)

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


    def test_status(self):
        """Is initial status 0? Can we set it?"""
        a = amcattest.create_test_coding()
        self.assertEqual(a.status.id, 0)
        self.assertEqual(a.status, CodingStatus.objects.get(pk=STATUS_NOTSTARTED))
        a.set_status(STATUS_INPROGRESS)
        self.assertEqual(a.status, CodingStatus.objects.get(pk=1))
        a.set_status(STATUS_COMPLETE)
        self.assertEqual(a.status, CodingStatus.objects.get(pk=2))
        a.set_status(STATUS_IRRELEVANT)
        self.assertEqual(a.status, CodingStatus.objects.get(pk=9))
        a.set_status(STATUS_NOTSTARTED)
        self.assertEqual(a.status, CodingStatus.objects.get(pk=0))
        
    def test_comments(self):
        """Can we set and read comments?"""
        a = amcattest.create_test_coding()
        self.assertIsNone(a.comments)

        for offset in range(4563, 20000, 1000):
            s = "".join(unichr(offset + c) for c in range(12, 1000, 100))
            a.comments = s
            a.save()
            a = Coding.objects.get(pk=a.id)
            self.assertEqual(a.comments, s)
            
    def test_create_value(self):
        """Can we create an coding value?"""
        a = amcattest.create_test_coding(codingjob=self.job)
        v = CodingValue.objects.create(coding=a, field=self.strfield,
                                           intval=1, strval="abc")
        v2 = CodingValue.objects.create(coding=a, field=self.intfield,
                                            intval=1, strval="abc")
        v3 = CodingValue.objects.create(coding=a, field=self.codefield,
                                            intval=self.c.id)
        
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

        # field does not exist in (newly created) schema
        self.assertRaises(ValueError, CodingValue.objects.create,
                          coding=amcattest.create_test_coding(),
                          field=self.strfield, strval="abc")
        
    def test_update_value(self):
        """Does update_value on a codingvalue work?"""
        a = amcattest.create_test_coding(codingjob=self.job)
        v = CodingValue.objects.create(coding=a, field=self.intfield, intval=1)
        v.update_value("99")
        self.assertEqual(v.value, 99)
        self.assertRaises(Exception, v.update_value, "abv")
        
        v2 = CodingValue.objects.create(coding=a, field=self.codefield, intval=self.c.id)
        v2.update_value(self.c2)
        self.assertEqual(v2.value, self.c2)
        
        self.assertRaises(Exception, v2.update_value, "abv")
        self.assertRaises(ValueError, v2.update_value, None)

        # c3 = amcattest.create_test_code(label="NOT IN CODEBOOK")
        # TODO CHECK VALIDATION

        

    def test_update_values(self):
        """Does update_values on an coding work?"""
        a = amcattest.create_test_coding(codingjob=self.job)
        self.assertEqual(_valuestr(a), "")
        a.set_value(self.intfield, 12)
        self.assertEqual(_valuestr(a), "number:12")
        a.update_values({self.strfield:"bla"})
        self.assertEqual(_valuestr(a), "text:'bla'")
        a.update_values({self.strfield:None, self.intfield:"999", self.codefield:self.c})
        
        self.assertEqual(_valuestr(a), "code:<Code: CODED>;number:999")
        
        newfield = CodingSchemaField.objects.create(
            codingschema=amcattest.create_test_schema(),
            label="text", fieldtype=self.strfield.fieldtype)
        self.assertRaises(ValueError, a.update_values, {newfield : "3"})


