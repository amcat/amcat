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
import json

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


from amcat.models import ArticleSet

try:
    from amcat.scripts.query import DemoPluginAction
except ImportError:
    from unittest import SkipTest
    raise SkipTest("Could not import DemoPluginAction")

from amcat.tools import amcattest


class TestRDemoPlugin(amcattest.AmCATTestCase):
    def setUp(self):
        self.aset = amcattest.create_test_set()
        self.project = self.aset.project
        self.user = User.objects.first()
        self.asets = ArticleSet.objects.filter(id=self.aset.id)

    def _run_action(self, data, is_json=True):
        data = {**{"output_type": "text/html"}, **data}
        aa = DemoPluginAction(self.user, self.project, self.asets, data=data)

        aa_form = aa.get_form()
        aa_form.full_clean()
        self.assertTrue(aa_form.is_bound)
        self.assertTrue(aa_form.is_valid())

        if is_json:
            return json.loads(aa.run(aa_form))

        return aa.run(aa_form)

    def test_demo_plugin_1(self):
        """Test escapes of tricky characters"""
        result = self._run_action(is_json=False, data={"field1": r"\o/", "field2": 10})
        self.assertEqual(result, r"Hello \o/ ( 10 )")

        result = self._run_action(is_json=False, data={"field1": r"'", "field2": 10})
        self.assertEqual(result, r"Hello ' ( 10 )")

        result = self._run_action(is_json=False, data={"field1": r'"', "field2": 10})
        self.assertEqual(result, r'Hello " ( 10 )')
