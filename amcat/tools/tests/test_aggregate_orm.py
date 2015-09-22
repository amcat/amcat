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

from amcat.tools import amcattest, aggregate_orm
from amcat.models import CodingSchemaField

class TestAggregateORM(amcattest.AmCATTestCase):
    def setUp(self):
        self.s1 = amcattest.create_test_set(4)
        self.a1, self.a2, self.a3, self.a4 = self.s1.articles.all()
        self.m1 = self.a1.medium
        self.m2 = self.a2.medium
        self.a3.medium = self.m2
        self.a3.save()
        
        self.schema, self.codebook, self.strf, self.intf, self.codef = (
            amcattest.create_test_schema_with_fields(isarticleschema=True))

        self.codes = self.codebook.get_codes()
        self.code_A, = [c for c in self.codes if c.label == "A"]
        self.code_B, = [c for c in self.codes if c.label == "B"]

        self.job = amcattest.create_test_job(articleset=self.s1, articleschema=self.schema)

        self.c1 = amcattest.create_test_coding(codingjob=self.job, article=self.a1)
        self.c1.update_values({self.codef: self.code_A.id, self.intf: 4})

        self.c2 = amcattest.create_test_coding(codingjob=self.job, article=self.a2)
        self.c2.update_values({self.codef: self.code_A.id, self.intf: 2})

        self.c3 = amcattest.create_test_coding(codingjob=self.job, article=self.a3)
        self.c3.update_values({self.codef: self.code_B.id, self.intf: 1})


    def _test_aggregate(self, x, val):
        "Conduct an aggregation and yield a 'settable' sequence" 
        aggr = aggregate_orm.ORMAggregate([self.job], [a.id for a in self.s1.articles.all()])
        if isinstance(x, CodingSchemaField):
            x = "schemafield_cat_{x.id}".format(**locals())
        if isinstance(val, CodingSchemaField):
            val = "schemafield_avg_{val.id}".format(**locals())
            
        
        for x, y in aggr.get_aggregate(x, val):
            _, val = y[0]
            yield x, val
        

    def test_avg_per_code(self):
        """Tests aggregate ORM with single aggregation and single value"""
        self.assertEqual(set(self._test_aggregate(self.codef, val=self.intf)),
                         {(self.code_A, 3.0), (self.code_B, 1.0)})
        
        self.assertEqual(set(self._test_aggregate("medium", val=self.intf)),
                         {(self.m1, 4.0), (self.m2, 1.5)})

        # does not work yet, orm requires a codebook aggregation atm
        self.assertEqual(set(self._test_aggregate(self.codef, val="count")),
                         {(self.code_A, 2), (self.code_B, 1)})

    def test_secondary_axis(self):
        """Test whether we can do count plus average per something"""
        # does not actually work yet, and not sure what signature/result structure should look like
        # since now it is done by second aggregate call

        
        self.assertEqual(set(self._test_aggregate(self.codef, val="count", val2=self.intf)),
                         {(self.code_A, (2, 3.0)), (self.code_B, (1, 1.0))})
        
        
        
    def test_medium_per_code(self):
        """Test whether we can use code field as secondary aggregation"""
        # does not actually work yet, and not sure what signature/result structure should look like
        
        self.assertEqual(set(self._test_aggregate("medium", self.codef, val="count")),
                         {(self.m1, self.code_A, 1),
                          (self.m2, self.code_A, 1),
                          (self.m2, self.code_B, 1)})

        
        self.assertEqual(set(self._test_aggregate("medium", self.codef, val=self.intf)),
                         {(self.m1, self.code_A, 4.0),
                          (self.m2, self.code_A, 2.0),
                          (self.m2, self.code_B, 1.0)})

        
    def test_illegal_aggregate(self):
        """Having a second value and second aggregation should throw an exception"""
        self.assertRaises(Exception,
                          set(self._test_aggregate("medium", self.codef, val="count", val2=self.intf)))
        
        
