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
Testing module to test # of queries used for retrieving manual codings
"""

from __future__ import unicode_literals, print_function, absolute_import

from amcat.model.language import Language
from amcat.model.coding import codebook
from amcat.model.coding.codingschemafield import CodingSchemaField
from amcat.model.coding.codingschemafield import CodingSchemaFieldType

from amcat.tools import amcattest

import random

class TestNQueries(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = ["W0613"]

    def setUp(self):
        super(TestNQueries, self).setUp()
        self.texttype = CodingSchemaFieldType.objects.get(pk=1)
        self.inttype = CodingSchemaFieldType.objects.get(pk=2)
        self.codetype = CodingSchemaFieldType.objects.get(pk=5)
        self.codebook = amcattest.create_test_codebook()
        self.code = self.codebook.add_code(amcattest.create_test_code(label="CODED")).code

    def _create_job(self, fieldtypes):
        """Create a job whose schemas contain the given fields"""
        schema = amcattest.create_test_schema()

        for i, t in enumerate(fieldtypes):
            CodingSchemaField.objects.create(codingschema=schema, fieldnr=i, fieldtype=t,
                                             label="field%i" % i, codebook = self.codebook)
        return amcattest.create_test_job(articleschema=schema, unitschema=schema)

    def _add_codings(self, job, codings, narticles=10):
        """Add codings (list-of-lists) to a job"""

        s = amcattest.create_test_set(articles=narticles)
        articles = list(s.articles.all())
                
        fields = list(job.unitschema.fields.all())
        result = []
        for values in codings:
            random.shuffle(articles)
            c = amcattest.create_test_coding(codingjob=job, article=articles[0])
            c.update_values(dict(zip(fields, values)))
            result.append(c)
        return result # don't use iterator to allow use as statement (eg non-lazy eval)


    def test_get_values(self):
        """Test whether get_values is cached for primitive types"""

        j = self._create_job([self.inttype, self.inttype, self.texttype])
        vals = [1, 2, "bla"]
        c, = self._add_codings(j, [vals])
        with self.checkMaxQueries(1, "Get values on one coding"):
            vals2 = [v for (_k, v) in c.get_values()]
            self.assertEqual(vals, vals2)
        with self.checkMaxQueries(0, "Cached get_values"):
            vals2 = [v for (_k, v) in c.get_values()]
            self.assertEqual(vals, vals2)
        

    def test_ontology_deserialisation_low_level(self):
        """Test whether deserialisation from the ontology using low-level calls is efficient"""
        c1, _c2 = self._add_codings(self._create_job([self.codetype]), [(self.code,), (self.code,)])

        with self.checkMaxQueries(2, "Cache codebook"):
            self.codebook.get_hierarchy()
            
        with self.checkMaxQueries(1, "get values"):
            q = c1.values.order_by('field__fieldnr')
            q = q.select_related("field__fieldtype", "value__strval", "value__intval")
            value, = list(q)
            
        with self.checkMaxQueries(0, "get serialised value from select_related"):
            serval = value.serialised_value

        with self.checkMaxQueries(0, "Get serialiser, fieldtype should be in select_related"):
            serialiser = value.field.serialiser
            
        with self.checkMaxQueries(0, "Deserialise codebook value"):
            code = serialiser.deserialise(serval)
            self.assertEqual(code, self.code)
            
    def test_ontology_deserialisation(self):
        """Test whether normal ontology deserialization is efficient"""
        c1, c2 = self._add_codings(self._create_job([self.codetype]), [(self.code,)]*2)

        
        with self.checkMaxQueries(2, "Cache codebook"):
            self.codebook.get_hierarchy()
            
        with self.checkMaxQueries(2, "Get codingvalue for one coding"):
            code, = [v for (_k, v) in c1.get_values()]
            self.assertEqual(self.code, code)

        with self.checkMaxQueries(1, "Get codingvalue for a second coding"):
            code, = [v for (_k, v) in c2.get_values()]
            self.assertEqual(self.code, code)

    def test_codebook_lookup(self):
        """Test whether looking things up in a code book is efficient"""
        A = amcattest.create_test_codebook()
        last = None
        for i in range(100):
            last = A.add_code(amcattest.create_test_code(label=str(i)), last)
        with self.checkMaxQueries(2, "Code membership"):
            _x = [a.id for a in A.codes]
        with self.checkMaxQueries(0, "Code membership (cached)"):
            _x = [a.id for a in A.codes]


    def test_codebook_base_lookup(self):
        """Test whether looking things up in a code book with bases is efficient"""
        A = amcattest.create_test_codebook()
        for i in range(100):
            c = A.add_code(amcattest.create_test_code(label=str(i)), None)

        B = amcattest.create_test_codebook(name="D+B")
        B.add_base(A)
        for i in range(100):
            B.add_code(amcattest.create_test_code(label=str(i)), None)

	# 2 to get bases, 2 to get codes, 1 to get base codebook
        with self.checkMaxQueries(5, "Subcodebook code list"):
            self.assertEqual(len(list(B.codes)), 200)
            
        with self.checkMaxQueries(0, "Subcodebook code membership (cached)"):
            self.assertIn(c.code, B.codes)
        
    def test_codebook_labels(self):
        """Does caching the codebook_labels work"""
        language = Language.objects.get(pk=1)
        A = amcattest.create_test_codebook()
        for i in range(100):
            A.add_code(amcattest.create_test_code(label=str(i), language=language), None)
        codes = list(A.codes)
        with self.checkMaxQueries(1, "Caching labels for a codebook"):
            A.cache_labels(language)
        with self.checkMaxQueries(0, "Getting cached labels for a codebook"):
            for x in codes:
                x.get_label(language)

        

        
    def test_jobset_allcodes(self):
        """Test whether getting all codes for a set is efficient"""
        types = [self.inttype, self.codetype]
        vals = [(12, self.code)]
        job = self._create_job(types)
        codings = self._add_codings(job, vals * 25, narticles=1)

        with self.checkMaxQueries(2, "Caching codebook"):
            c = codebook.get_codebook(self.codebook.id)
            list(c.get_hierarchy())
            
        with self.checkMaxQueries(1, "Getting all codings for a job"):
            codings = list(job.get_codings())

        with self.checkMaxQueries(0, "Getting pre-fetched codings and values"):
            for c in codings:
                _x = [v for (_k, v) in c.get_values()]

                
