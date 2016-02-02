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
from __future__ import unicode_literals, print_function, absolute_import


class Tree(object):
    """Simple representation of a tree, providing various functions and constructors"""
    def __init__(self, obj, children=(), parent=None):
        self.obj = obj
        self.children = children
        self.parent = parent

    def traverse(self, func=lambda e: e):
        """Traverse over tree. Optionally takes a function which is applied
        to the object and its result yielded."""
        yield func(self)
        for child in self.children:
            for tree in child.traverse(func):
                yield tree

    def get_level(self, depth):
        if not depth:
            yield self
        else:
            for child in self.children:
                for tree in child.get_level(depth - 1):
                    yield tree

    @classmethod
    def from_tuples(cls, tup, parent=None):
        """Instantiate tree from a list of tuples of (element, [children])"""
        obj, children = tup
        new_tree = cls(obj, parent=parent)
        new_tree.children = [cls.from_tuples(c, parent=new_tree) for c in children]
        return new_tree

    def __eq__(self, other):
        return self.parent == other.parent and self.obj == other.obj and self.children == other.children

