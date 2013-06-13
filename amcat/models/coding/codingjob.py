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

from functools import partial

from amcat.tools.model import AmcatModel
from amcat.tools.caching import set_cache
from amcat.tools.table import table3 


from amcat.models.coding.codingschema import CodingSchema
from amcat.models.coding.codingschemafield import CodingSchemaField
from amcat.models.coding.coding import Coding
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

    def get_codings(self):
        """Return a sequence of codings with pre-fetched values"""
        # late import to prevent cycles
        from amcat.models.coding.coding import CodingValue
        
        q = CodingValue.objects.filter(coding__codingjob__exact=self)
        q = q.select_related("field__fieldtype", "value__strval", "value__intval", "coding")
        q = q.order_by("coding", 'field__fieldnr')
        # possible optimzation: use running values list because of sort order
        values_per_coding = {} # coding : [(field, value), ...]
        for val in q:
            values_per_coding.setdefault(val.coding, []).append((val.field,  val.value))
        for coding, values in values_per_coding.iteritems():
            set_cache(coding, coding.get_values.__name__, values)
            yield coding

    def values_table(self, unit_codings=False):
        """
        Return the coded values in this job as a table3.Table with codings as rows
        and the fields in the columns; cells contain serialised values. 
        """
        schema_id = self.unitschema_id if unit_codings else self.articleschema_id
        fields = CodingSchemaField.objects.filter(codingschema=schema_id)
        columns = [SchemaFieldColumn(field) for field in fields]
        codings = Coding.objects.filter(codingjob=self, sentence__isnull=(not unit_codings))
        codings = codings.prefetch_related("values", "values__field")
        codings = list(codings)
        return table3.ObjectTable(rows=codings, columns=columns)
    
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

class TestCodingJob(amcattest.PolicyTestCase):
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
        
    def test_values_table(self):
        """Does getting a table of values work?"""
        
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields()
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema)
        
        c = amcattest.create_test_coding(codingjob=job)
        c.update_values({strf:"bla", intf:1})
	
        self.assertEqual(set(job.values_table().to_list()), {('bla', 1, None)})

        code = amcattest.create_test_code(label="CODED")
        codebook.add_code(code)
        c2 = amcattest.create_test_coding(codingjob=job)
        c2.update_values({intf:-1, codef: code})
        t = job.values_table()
        self.assertEqual(set(t.rows), {c, c2})
        self.assertEqual(set(t.to_list()), {('bla', 1, None), (None, -1, code.id)})

    def test_nqueries(self):
        """Does getting a table of values not use too many queries?"""
        
        schema, codebook, strf, intf, codef = amcattest.create_test_schema_with_fields()
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema)

        for i in range(10):
            c = amcattest.create_test_coding(codingjob=job)
            c.update_values({strf:"bla %i"%i, intf:i})

        job = CodingJob.objects.get(pk=job.id)
        with self.checkMaxQueries(6):
            # 1. get schema, 2. get codings, 3. get values, 4. get field, 5+6. get serialiser
            t = job.values_table()
            cells = list(t.to_list())
