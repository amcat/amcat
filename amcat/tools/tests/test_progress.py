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
import unittest

from amcat.tools.progress import ProgressMonitor


class TestProgressMonitor(unittest.TestCase):
    def test_submonitors(self):
        monitor = ProgressMonitor(total=5)
        monitor.update(2)

        sm1 = monitor.submonitor(2)
        sm2 = monitor.submonitor(2)
        sm3 = sm2.submonitor(2)

        # Submonitors have done no work, so 2 out of 5 steps
        self.assertAlmostEqual(monitor.get_progress(), 2/5)

        # Submonitors each account for one step in their parent
        sm1.update()
        self.assertAlmostEqual(monitor.get_progress(), 2/5 + 1/2 * 1/5)
        self.assertEqual(2, len(monitor.sub_monitors))

        # Submonitors deregister if done
        sm1.update()
        self.assertAlmostEqual(monitor.get_progress(), 3/5)
        self.assertEqual(1, len(monitor.sub_monitors))

        # Recursive submonitors should work
        sm3.update()
        self.assertAlmostEqual(monitor.get_progress(), 3/5 + 1/4 * 1/5)

        sm3.update()
        sm2.update()
        monitor.update()

        self.assertAlmostEqual(monitor.get_progress(), 1)
