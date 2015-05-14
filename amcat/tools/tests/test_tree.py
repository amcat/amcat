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
from operator import itemgetter
from unittest import TestCase
from amcat.tools.tree import Tree


class TestTree(TestCase):
    def setUp(self):
        self.tree = (
            "root", [
                ("child1", []),
                ("child2", [
                    ("child3", []), ("child4", [])
                ])]
        )

    def test_traverse(self):
        self.assertEqual(
            {"root", "child1", "child2", "child3", "child4"},
            set(t.obj for t in Tree.from_tuples(self.tree).traverse())
        )

        self.assertEqual(
            {"t", "1", "2", "3", "4"},
            set(Tree.from_tuples(self.tree).traverse(lambda x: x.obj[-1]))
        )

    def test_get_level(self):
        tree = Tree.from_tuples(self.tree)

        self.assertEqual(set(t.obj for t in tree.get_level(0)), {"root"})
        self.assertEqual(set(t.obj for t in tree.get_level(1)), {"child1", "child2"})
        self.assertEqual(set(t.obj for t in tree.get_level(2)), {"child3", "child4"})
        self.assertEqual(set(t.obj for t in tree.get_level(5)), set())
