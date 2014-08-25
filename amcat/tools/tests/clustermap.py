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
from __future__ import unicode_literals

from amcat.tools.amcattest import AmCATTestCase
from amcat.tools.clustermap import get_clusters, get_cluster_queries
from amcat.tools.keywordsearch import SearchQuery


class TestClusterMap(AmCATTestCase):
    def test_get_clusters(self):
        queries = {"a": [1, 2, 3], "b": [1, 4], "c": [1]}
        clusters = dict(get_clusters(queries))

        # Assert clusters
        self.assertIn(frozenset({'a', 'b', 'c'}), clusters)
        self.assertIn(frozenset({'a'}), clusters)
        self.assertIn(frozenset({'b'}), clusters)
        self.assertNotIn(frozenset({'c'}), clusters)
        self.assertNotIn(frozenset({'a', 'b'}), clusters)
        self.assertNotIn(frozenset({'c', 'a'}), clusters)
        self.assertNotIn(frozenset({'c', 'b'}), clusters)

        # Assert clustervalues
        self.assertEqual(clusters[frozenset({'a', 'b', 'c'})], {1})
        self.assertEqual(clusters[frozenset({'b'})], {4})
        self.assertEqual(clusters[frozenset({'a'})], {2, 3})

    def test_get_cluster_queries(self):
        queries = {
            SearchQuery("a"): [1, 2, 3],
            SearchQuery("b"): [1, 4],
            SearchQuery("c"): [1]
        }

        clusters = get_clusters(queries).keys()
        queries = set(get_cluster_queries(clusters))

        good_queries = [
            # get_cluter_queries generates queries undeterministically
            ('((b) AND (a) AND (c))', '((b) AND (c) AND (a))'),
            ('((a)) NOT ((b) OR (c))', '((a)) NOT ((c) OR (b))'),
            ('((b)) NOT ((c) OR (a))', '((b)) NOT ((a) OR (c))'),
        ]

        for q1, q2 in good_queries:
            self.assertTrue((q1 in queries) or (q2 in queries))

