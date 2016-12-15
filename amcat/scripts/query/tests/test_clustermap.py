##########################################################################
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
from collections import ChainMap

import base64
import json
import os
import shutil
import unittest

from amcat.scripts.query import ClusterMapAction
from amcat.tools import amcattest
from amcat.tools.amcates import ES

def _to_comparable(result):
    for r in result:
        yield tuple((k, (tuple(sorted(v)) if isinstance(v, list) else v)) for k,v in r.items())

def _strip_csv(s):
    return "\n".join(l.strip() for l in s.split("\n")).strip()

class TestClustermapAction(amcattest.AmCATTestCase):
    def set_up(self):
        self.project = amcattest.create_test_project()

        self.a1 = amcattest.create_test_article(text="aap noot mies")
        self.a2 = amcattest.create_test_article(text="aap noot")
        self.a4 = amcattest.create_test_article(text="aap noot")
        self.a3 = amcattest.create_test_article(text="aap")
        self.a5 = amcattest.create_test_article(text="vuur")

        amcattest.create_test_set((self.a1, self.a2, self.a3, self.a4, self.a5), project=self.project)
        ES().refresh()

    def get_query_action(self, output_type="application/json+clustermap", query="aap\nnoot\nmies\nv#vuur", **kwargs):
        return ClusterMapAction(
            user=self.project.owner, project=self.project,
            articlesets=self.project.all_articlesets(),
            data=dict(ChainMap({"output_type": output_type, "query": query}, kwargs))
        )

    @amcattest.use_elastic
    def test_json_clustermap(self):
        self.set_up()

        clustermap_action = self.get_query_action(query="aap\nnoot\nmies\nvuur")
        clustermap_form = clustermap_action.get_form()
        clustermap_form.full_clean()

        out = json.loads(clustermap_action.run(clustermap_form))

        # If the equality fails, get_cluster_queries might generate the queries non-deterministically
        expected_clusters = _to_comparable((
            {'articles': (self.a2.id, self.a4.id), 'query': '((aap) AND (noot)) NOT ((mies) OR (vuur))'},
            {'articles': (self.a1.id,), 'query': '((aap) AND (mies) AND (noot)) NOT ((vuur))'},
            {'articles': (self.a5.id,), 'query': '((vuur)) NOT ((aap) OR (mies) OR (noot))'},
            {'articles': (self.a3.id,), 'query': '((aap)) NOT ((mies) OR (noot) OR (vuur))'}
        ))

        self.assertEqual(set(expected_clusters), set(_to_comparable(out["clusters"])))
        self.assertTrue(out["image"].encode('ascii'))
        self.assertTrue(base64.b64decode(out["image"].encode("ascii")))


    @amcattest.use_elastic
    @unittest.skipUnless(shutil.which("pspp"), "PSPP not installed")
    def test_spss_sav(self):
        self.set_up()
        clustermap_action = self.get_query_action("application/spss-sav")
        clustermap_form = clustermap_action.get_form()
        clustermap_form.full_clean()
            
        filename = clustermap_action.run(clustermap_form)
        self.assertTrue(os.path.exists(filename))
        self.assertTrue(os.path.getsize(filename) > 0)

    @amcattest.use_elastic
    def test_csv(self):
        self.set_up()

        clustermap_action = self.get_query_action("text/csv", )
        clustermap_form = clustermap_action.get_form()
        clustermap_form.full_clean()

        expected = _strip_csv("""
            aap,mies,noot,v,Total
            0,0,0,1,1
            1,0,0,0,1
            1,0,1,0,2
            1,1,1,0,1
        """)

        csv = clustermap_action.run(clustermap_form)
        self.assertEqual(_strip_csv(csv), _strip_csv(expected))

    @amcattest.use_elastic
    def test_json_clustermap_table(self):
        self.set_up()

        clustermap_action = self.get_query_action("application/json+clustermap+table")
        clustermap_form = clustermap_action.get_form()
        clustermap_form.full_clean()

        table = json.loads(clustermap_action.run(clustermap_form))

        expected = _strip_csv("""
            aap,mies,noot,v,Total
            0,0,0,1,1
            1,0,0,0,1
            1,0,1,0,2
            1,1,1,0,1
        """)

        self.assertEqual(_strip_csv(table["csv"]), _strip_csv(expected))
        self.assertEqual(table["queries"], {
            "noot": "noot",
            "aap": "aap",
            "mies": "mies",
            "v": "vuur"
        })
