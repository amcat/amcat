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

from amcat.tools import amcattest
from amcat.tools.toolkit import read_date

from api.rest.tablerenderer import TableRenderer

class TestTableRenderer(amcattest.AmCATTestCase):
    def _test(self, d, header, data):
        t = TableRenderer().tablize(d)
        # check contents are the same while allowing for header order changes
        mapping = {str(col): i for (i, col) in enumerate(t.get_columns())}
        self.assertEqual(set(header), set(mapping))
        found = [tuple(row[mapping[h]] for h in header)
                 for row in t.to_list(tuple_name=None)]
        #import json; print(json.dumps(found, indent=2))
        self.assertEqual(data, found)
    
    def test_tablize(self):
        self._test([{"a": 1}], ["a"], [(1,)])

        self._test([{"a": 1, "c": 3}, {"a": 1, "b": 2}], ["a", "c", "b"], [(1, 3, None), (1, None, 2)])

        self._test([{"a": 1, "c": 3}, {"a": 1, "b": {"x": "X", "y": "Y"}}],
                    ["a", "c", "b.x", "b.y"], [(1, 3, None, None), (1, None, "X", "Y")])


        self._test([{"a": 1, "c": 3}, {"a": 4, "d": [{"a":"DA"}, {"b":"DB"}]}],
                   ["a", "c", "d.0.a", "d.1.b"],
                   [(1, 3, None, None), (4, None, "DA", "DB")])
