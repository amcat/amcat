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
from amcat.tools import amcates
from amcat.tools import amcattest
from amcat.tools.association import Association
from amcat.tools.keywordsearch import SearchQuery


class TestAssociation(amcattest.AmCATTestCase):
    def set_up(self):
        self.aset = amcattest.create_test_set()
        self.a1 = amcattest.create_test_article(text="de de het", articleset=self.aset)
        self.a2 = amcattest.create_test_article(text="de", articleset=self.aset)
        self.a3 = amcattest.create_test_article(text="een", articleset=self.aset)

        self.de = SearchQuery.from_string("de")
        self.het = SearchQuery.from_string("het")
        self.aap = SearchQuery.from_string("aap")

        self.filters = {"sets": [self.aset.id]}
        amcates.ES().refresh()

        self.ass = Association([self.de, self.het], self.filters)

    @amcattest.use_elastic
    def test_get_conditional_probabilities(self):
        self.set_up()

        self.assertEqual(set(self.ass.get_conditional_probabilities()), {
            (None, 1.0, self.de, self.de),
            (None, 1.0, self.het, self.het),
            (None, 0.5, self.de, self.het),
            (None, 1.0, self.het, self.de),
        })

    @amcattest.use_elastic
    def test_get_conditional_probabilities_weighted(self):
        self.set_up()
        ass = Association([self.de, self.het], self.filters, weighted=True)

        self.assertEqual(set(ass.get_conditional_probabilities()), {
            (None, 1.0, self.de, self.de),
            (None, 1.0, self.het, self.het),
            (None, 0.3, self.de, self.het),
            (None, .75, self.het, self.de),
        })

    @amcattest.use_elastic
    def test_get_table(self):
        self.set_up()

        # get_table() should ignore P(X|Y) where X = Y.
        headers, rows = self.ass.get_table()
        self.assertEqual(set(rows), {
            (None, self.de, self.het, '0.5'),
            (None, self.het, self.de, '1.0'),
        })

    @amcattest.use_elastic
    def test_get_crosstables(self):
        self.set_up()

        tables = list(self.ass.get_crosstables())
        interval, table = tables[0]
        table = list(table)
        headers, rows = table[0], table[1:]

        self.assertEqual(1, len(tables))
        self.assertEqual(headers, ("",) + self.ass.get_queries())
        self.assertEqual(set(rows), {
            (self.de, '1.0', '0.5'),
            (self.het, '1.0', '1.0')
        })

    @amcattest.use_elastic
    def test_empty_values(self):
        self.set_up()


        ass = Association([self.het, self.aap], self.filters)

        interval, table = next(ass.get_crosstables())
        table = list(table)
        headers, rows = table[0], table[1:]

        self.assertEqual(set(rows), {
            (self.aap, '-', '-'),
            (self.het, '-', '1.0'),
        })

