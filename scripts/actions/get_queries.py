#!/usr/bin/python

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
Script to get queries for a codebook
"""

import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.models.coding.codebook import Codebook, get_codebook
from amcat.tools.table.table3 import Table, ObjectTable

LABEL_LANGUAGE = 2,1,
QUERY_LANGUAGE = 13,

class GetQueries(Script):
    class options_form(forms.Form):
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all())
        
    output_type = Table
    
    def run(self, _input=None):
        c = get_codebook(self.options["codebook"].id)
        for lang in LABEL_LANGUAGE + QUERY_LANGUAGE:
            c.cache_labels(lang)
        t = ObjectTable(rows=c.get_codes())
        t.addColumn(lambda c : c.id, "id")
        t.addColumn(lambda c : c.get_label(*LABEL_LANGUAGE) , "label")
        t.addColumn(lambda c : c.get_label(*QUERY_LANGUAGE, fallback=False) , "query")
        return t
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()
        

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestGetQueries(amcattest.PolicyTestCase):
    
    def test_label(self):
        from amcat.models.coding.code import get_code
        from amcat.models import Language
        l = Language.objects.create(id=13, label='query')
        
        a = amcattest.create_test_code(label="test") 
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        a = get_code(a.id)

        t = GetQueries(codebook=A.id).run()
        result = set(tuple(row) for row in t)
        self.assertEqual(result, set([(a.id, "test", None)]))

        a.add_label(l, "bla")

        t = GetQueries(codebook=A.id).run()
        result = set(tuple(row) for row in t)
        self.assertEqual(result, set([(a.id, "test", "bla")]))

    def test_nqueries(self):
        from amcat.models.coding.code import Code
        from amcat.tools.caching import clear_cache
        from amcat.models import Language
        l = Language.objects.create(id=13, label='query')
        
        A = amcattest.create_test_codebook(name="A")
        codes = []
        N = 20
        for i in range(N):
             code = amcattest.create_test_code(label="test") 
             A.add_code(code)
             code.add_label(l, "query")
             codes.append(code)

        
        clear_cache(Code)
        with self.checkMaxQueries(7): # 3 for language, 2 for codes, 1 for bases, 1 for codebook
            t = GetQueries(codebook=A.id).run()
            result = set(tuple(row) for row in t)
        code = codes[3]
        self.assertIn((code.id, "test", "query"), result)
        self.assertEqual(len(result), N)

