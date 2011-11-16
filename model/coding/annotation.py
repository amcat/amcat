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
        if stype == str: return self.strval
        return self.intval

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

    @property
    def sentence_annotations(self):
        """Get the sentence annotations for this coded article"""
        return self.codingjobset.annotations.filter(article=self.article, sentence__isnull=False)
        
    
    
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
            
    def test_create_value(self):
        """Can we create an annotation value?"""
        from amcat.model.coding.annotationschemafield import AnnotationSchemaFieldType
        strfieldtype = AnnotationSchemaFieldType.objects.get(pk=1)
        intfieldtype = AnnotationSchemaFieldType.objects.get(pk=2)
        codefieldtype = AnnotationSchemaFieldType.objects.get(pk=5)


        codebook = amcattest.create_test_codebook()
        c = amcattest.create_test_code(label="CODED")
        codebook.add_code(c)

        schema = amcattest.create_test_schema()
        strfield = AnnotationSchemaField.objects.create(annotationschema=schema, fieldnr=1,
                                                        fieldtype=strfieldtype)
        intfield = AnnotationSchemaField.objects.create(annotationschema=schema, fieldnr=2,
                                                        fieldtype=intfieldtype)
        codefield = AnnotationSchemaField.objects.create(annotationschema=schema, fieldnr=3,
                                                        fieldtype=codefieldtype, codebook=codebook)
        a = amcattest.create_test_annotation()
        v = AnnotationValue.objects.create(annotation=a, field=strfield, intval=1, strval="abc")
        v2 = AnnotationValue.objects.create(annotation=a, field=intfield, intval=1, strval="abc")


        v3 = AnnotationValue.objects.create(annotation=a, field=codefield, intval=c.id)
        
        self.assertIn(v, a.values.all())
        self.assertEqual(v.value, "abc")
        self.assertEqual(v2.value, 1)
        self.assertEqual(v3.value, c)

        self.assertEqual(list(a.get_values()), [(strfield, "abc"), (intfield, 1), (codefield, c)])
        
    def test_codedarticle(self):
        """Test whether CodedArticle annotation retrieval works"""
        a = amcattest.create_test_annotation()
        s = amcattest.create_test_sentence()
        a2 = amcattest.create_test_annotation(sentence=s, codingjobset=a.codingjobset)
        a3 = amcattest.create_test_annotation(sentence=s, codingjobset=a.codingjobset)
        ca = CodedArticle(a)

        self.assertEqual(set(ca.sentence_annotations), {a2, a3})
        self.assertEqual(ca.annotation, a)
        
        
