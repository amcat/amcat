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
import unittest

from django.db import models
from django.conf import settings
from exportable.columns import IntColumn

from api5.table import DeclaredModelTable

# Allow tests without actual Django environment
settings.configure(DEBUG=True)

class FooModel(models.Model):
    text = models.TextField()
    length = models.IntegerField()
    added = models.DateTimeField()

    class Meta:
        app_label = "foo"


class TestDeclaredModelTable(unittest.TestCase):
    def test_simple(self):
        """Test model instance without any extra options"""
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel

        self.assertEqual(
            [c.label for c in FooModelTable._get_columns()],
            ["id", "text", "length", "added"]
        )

    def test_exclude(self):
        """Test model instnace with exclude"""
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel
                exclude = ("text",)

        self.assertEqual(
            [c.label for c in FooModelTable._get_columns()],
            ["id", "length", "added"]
        )

    def test_include(self):
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel
                include = ("id",)

        self.assertEqual(["id"], [c.label for c in FooModelTable._get_columns()])

    def test_include_and_exclude(self):
        """Should raise an error if both include an exclude are defined."""
        # Both filled
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel
                include = ("id",)
                exclude = ("text",)

        self.assertRaises(ValueError, FooModelTable._get_columns)

        # Both empty
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel
                include = ()
                exclude = ()

        self.assertRaises(ValueError, FooModelTable._get_columns)

    def test_unknown_option(self):
        """Should error if unkown option is given"""
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel
                abc = "test"

        self.assertRaises(ValueError, FooModelTable._get_columns)

    def test_no_model(self):
        # Implicitly
        class FooModelTable(DeclaredModelTable):
            pass
        self.assertRaises(ValueError, FooModelTable._get_columns)

        # Explicitly
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = None
        self.assertRaises(ValueError, FooModelTable._get_columns)

    def test_inheritance(self):
        class FooModelTable(DeclaredModelTable):
            class Meta:
                model = FooModel
                exclude = ("text",)

        # Empty Meta
        class BarModelTable(FooModelTable):
            icolumn = IntColumn()
            class Meta(FooModelTable.Meta):
                pass

        self.assertEqual(
            [c.label for c in BarModelTable._get_columns()],
            ["id", "length", "added", "icolumn"]
        )

        # No Meta
        class BarModelTable(FooModelTable):
            icolumn = IntColumn()

        self.assertEqual(
            [c.label for c in BarModelTable._get_columns()],
            ["id", "length", "added", "icolumn"]
        )

        # Extend exclude
        class BarModelTable(FooModelTable):
            icolumn = IntColumn()
            class Meta(FooModelTable.Meta):
                exclude = ("length", "text")

        self.assertEqual(
            [c.label for c in BarModelTable._get_columns()],
            ["id", "added", "icolumn"]
        )
