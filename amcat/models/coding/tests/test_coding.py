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
from amcat.models import CodingValue
from amcat.tools import amcattest


class TestCoding(amcattest.AmCATTestCase):
    def setUp(self):
        """Set up a simple codingschema with fields to use for testing"""
        super(TestCoding, self).setUp()

        self.schema, self.codebook, self.strfield, self.intfield, self.codefield, _, _ = (
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
        self.assertIn(a.coded_article.article, j.articleset.articles.all())
        self.assertEqual(a.schema, schema2)
        a2 = amcattest.create_test_coding(codingjob=j,
                                          sentence=amcattest.create_test_sentence())
        self.assertEqual(a2.schema, self.schema)

    def test_update_values(self):
        codebook, codes = amcattest.create_test_codebook_with_codes()
        schema, codebook, strf, intf, codef, _, _ = amcattest.create_test_schema_with_fields(codebook=codebook)
        job = amcattest.create_test_job(unitschema=schema, articleschema=schema, narticles=7)
        articles = list(job.articleset.articles.all())

        coding = amcattest.create_test_coding(codingjob=job, article=articles[0])
        self.assertEqual(0, coding.values.count())
        coding.update_values({strf: "bla", intf: 1, codef: codes["A1b"].id})
        self.assertEqual(3, coding.values.count())
        self.assertTrue(strf in dict(coding.get_values()))
        self.assertTrue(intf in dict(coding.get_values()))
        self.assertTrue(codef in dict(coding.get_values()))
        self.assertEqual(1, dict(coding.get_values())[intf])

        # Does update_values delete values not present in dict?
        coding.update_values({strf: "blas"})
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
