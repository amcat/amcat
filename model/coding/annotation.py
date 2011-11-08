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

from amcat.tools.model import AmcatModel
from django.db import models

from amcat.model.coding.codingjob import CodingJobSet
from amcat.model.coding.annotationschemafield import AnnotationSchemaField
from amcat.model.article import Article
from amcat.model.sentence import Sentence

import logging; log = logging.getLogger(__name__)
            
class Annotation(AmcatModel):
    """
    Model class for annotations. Annotations provide the link between a Coding Job Set
    and actual Annotation Values. 
    """

    id = models.AutoField(primary_key=True, db_column='annotation_id')
    
    codingjobset = models.ForeignKey(CodingJobSet)
    article = models.ForeignKey(Article)
    sentence = models.ForeignKey(Sentence, null=True)
    
    class Meta():
        db_table = 'annotations'
        app_label = 'amcat'

class AnnotationValue(AmcatModel):
    """
    Model class for annotation values. 
    """
    
    id = models.AutoField(primary_key=True, db_column='annotationvalue_id')

    annotation = models.ForeignKey(Annotation, related_name='values')
    field = models.ForeignKey(AnnotationSchemaField)

    strval = models.CharField(blank=True, null=True, max_length=80)
    intval = models.IntegerField(null=True)
        
    class Meta():
        db_table = 'annotations_values'
        app_label = 'amcat'

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestAnnotation(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create an annotation?"""
        j = amcattest.create_test_job()
        s = amcattest.create_test_set(articles=2)
        cs = CodingJobSet.objects.create(codingjob=j, articleset=s, coder=j.insertuser)
        a = Annotation.objects.create(codingjobset=cs, article=s.articles.all()[0])
        self.assertIsNotNone(a)
        self.assertIn(a.article, s.articles.all())
        self.assertEqual(a.codingjobset.codingjob, j)

class TestAnnotationValue(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create an annotation value?"""
        from amcat.model.coding.annotationschemafield import AnnotationSchemaFieldType
        fieldtype = AnnotationSchemaFieldType.objects.get(pk=1)
        schema = amcattest.create_test_schema()
        field = AnnotationSchemaField.objects.create(annotationschema=schema, fieldnr=1,
                                                     fieldtype=fieldtype)

        j = amcattest.create_test_job(unitschema=schema)
        s = amcattest.create_test_set(articles=2)
        cs = CodingJobSet.objects.create(codingjob=j, articleset=s, coder=j.insertuser)
        a = Annotation.objects.create(codingjobset=cs, article=s.articles.all()[0])

        v = AnnotationValue.objects.create(annotation=a, field=field)
        self.assertIn(v, a.values.all())
