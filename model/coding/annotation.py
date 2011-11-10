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
Model module containing Annotations

An annotation is a hook for the annotation values on a specific article linked
to a specific coding job set.
"""

import logging; log = logging.getLogger(__name__)

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.tools.idlabel import Identity
from amcat.model.coding.codingjob import CodingJobSet
from amcat.model.coding.annotationschemafield import AnnotationSchemaField
from amcat.model.article import Article
from amcat.model.sentence import Sentence


class AnnotationStatus(AmcatModel):
    """
    Helder class for annotation status
    """

    id = models.IntegerField(primary_key=True, db_column='status_id')
    label = models.CharField(max_length=50)

    def __unicode__(self):
        return self.label
    
    class Meta():
        db_table = 'annotations_status'
        app_label = 'amcat'


STATUS_NOTSTARTED, STATUS_INPROGRESS, STATUS_COMPLETE, STATUS_IRRELEVANT = 0, 1, 2, 9
        
class Annotation(AmcatModel):
    """
    Model class for annotations. Annotations provide the link between a Coding Job Set
    and actual Annotation Values. 
    """

    id = models.AutoField(primary_key=True, db_column='annotation_id')
    
    codingjobset = models.ForeignKey(CodingJobSet, related_name="annotations")
    article = models.ForeignKey(Article)
    sentence = models.ForeignKey(Sentence, null=True)

    comments = models.TextField(blank=True, null=True)
    status = models.ForeignKey(AnnotationStatus, default=0)
    
    class Meta():
        db_table = 'annotations'
        app_label = 'amcat'
        
    def get_values(self):
        """Return a sequence of field, (deserialized) value pairs"""
        for value in self.values.all():
            yield value.field, value.value

    def update_values(self, values):
        """Update the current values

        @param values: mapping of field or fieldname to serialised value
        """
        raise NotImplementedError()

    def set_status(self, status):
        """Set the status of this annotation, deserialising status as needed"""
        if type(status) == int: status = AnnotationStatus.objects.get(pk=status)
        self.status = status
        
class AnnotationValue(AmcatModel):
    """
    Model class for annotation values. 
    """
    
    id = models.AutoField(primary_key=True, db_column='annotationvalue_id')

    annotation = models.ForeignKey(Annotation, related_name='values')
    field = models.ForeignKey(AnnotationSchemaField)

    strval = models.CharField(blank=True, null=True, max_length=80)
    intval = models.IntegerField(null=True)

    @property
    def serialised_value(self):
        """Get the 'serialised' (raw) value for this annotationvalue"""
        stype = self.field.serialiser.deserialised_type
        if stype == int: return self.intval
        if stype == str: return self.strval
        raise ValueError("Unknown deserialised type in %s: %s" % (self.field, stype) )

    @property
    def value(self):
        """Get the 'deserialised' (object) value for this annotationvalue"""
        return self.field.serialiser.deserialise(self.serialised_value)
    
    class Meta():
        db_table = 'annotations_values'
        app_label = 'amcat'
        unique_together = ("annotation", "field")


class CodedArticle(Identity):
    """Convenience class to represent an article in a codingjobset
    and expose the article annotation"""
    def __init__(self, codingjobset, article, annotation=False):
        super(CodedArticle, self).__init__(codingjobset.id, article.id)
        self.codingjobset = codingjobset
        self.article = article
        if annotation is not False:
            self._annotation = annotation
    @property
    def annotation(self):
        """Get the (cached) article annotation for this coded article"""
        try:
            return self._annotation
        except AttributeError:
            result = self.codingjobset.annotations.filter(article=self.article, sentence=None)
            if result: self._annotation = result[0]
            else: self._annotation = None
            return self._annotation
    
        
    
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestAnnotation(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create an annotation?"""
        a = amcattest.create_test_annotation()
        self.assertIsNotNone(a)
        self.assertIn(a.article, a.codingjobset.articleset.articles.all())

    def test_values(self):
        """Can we update and get values using the convenience functions?"""
        a = amcattest.create_test_annotation()
        a.update_values({})
        a.get_values()

    def test_status(self):
        """Is initial status 0? Can we set it?"""
        a = amcattest.create_test_annotation()
        self.assertEqual(a.status.id, 0)
        self.assertEqual(a.status, AnnotationStatus.objects.get(pk=STATUS_NOTSTARTED))
        a.set_status(STATUS_INPROGRESS)
        self.assertEqual(a.status, AnnotationStatus.objects.get(pk=1))
        a.set_status(STATUS_COMPLETE)
        self.assertEqual(a.status, AnnotationStatus.objects.get(pk=2))
        a.set_status(STATUS_IRRELEVANT)
        self.assertEqual(a.status, AnnotationStatus.objects.get(pk=9))
        a.set_status(STATUS_NOTSTARTED)
        self.assertEqual(a.status, AnnotationStatus.objects.get(pk=0))
        
    def test_comments(self):
        """Can we set and read comments?"""
        a = amcattest.create_test_annotation()
        self.assertIsNone(a.comments)

        for offset in range(4563, 20000, 1000):
            s = "".join(unichr(offset + c) for c in range(12, 1000, 100))
            a.comments = s
            a.save()
            a = Annotation.objects.get(pk=a.id)
            self.assertEqual(a.comments, s)
            
        
        

class TestAnnotationValue(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create an annotation value?"""
        from amcat.model.coding.annotationschemafield import AnnotationSchemaFieldType
        strfieldtype = AnnotationSchemaFieldType.objects.get(pk=1)
        intfieldtype = AnnotationSchemaFieldType.objects.get(pk=2)
        schema = amcattest.create_test_schema()
        strfield = AnnotationSchemaField.objects.create(annotationschema=schema, fieldnr=1,
                                                        fieldtype=strfieldtype)
        intfield = AnnotationSchemaField.objects.create(annotationschema=schema, fieldnr=2,
                                                        fieldtype=intfieldtype)

        a = amcattest.create_test_annotation()
        v = AnnotationValue.objects.create(annotation=a, field=strfield, intval=1, strval="abc")
        v2 = AnnotationValue.objects.create(annotation=a, field=intfield, intval=1, strval="abc")
        
        self.assertIn(v, a.values.all())
        self.assertEqual(v.value, "abc")
        self.assertEqual(v2.value, 1)

        self.assertEqual(list(a.get_values()), [(strfield, "abc"), (intfield, 1)])
