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
from amcat.models import Language
from amcat.scripts.actions.export_codebook import ExportCodebook
from amcat.tools import amcattest
from amcat.tools.amcattest import AmCATTestCase


class TestExportCodebook(AmCATTestCase):
    def setUp(self):
        self.de = Language.objects.get(label="de")
        self.nl = Language.objects.get(label="nl")
        self.default = Language.objects.get(id=1)

        self.codebook = amcattest.create_test_codebook_with_codes()[0]
        self.codes_list = list(self.codebook.codes.all())
        self.codes_list[0].add_label(self.de, "Ein")
        self.codes_list[1].add_label(self.nl, "Een")

    def export(self, codebook=None, language=None, structure="indented", labelcols=False):
        """Run ExportCodebook with some default arguments. Returns tableObj."""
        codebook = codebook or self.codebook
        language = language or self.default

        return {c.code_id : c for c in ExportCodebook(
            codebook=codebook.id, language=language.id,
            structure=structure, labelcols=labelcols
        ).run().to_list()}

    def test_indented(self):
        """Test indented format."""
        codes = self.export()

        # Depth of tree is 3, so we need exactly three columns
        self.assertTrue(hasattr(codes.values()[0], "code1"))
        self.assertTrue(hasattr(codes.values()[0], "code2"))
        self.assertTrue(hasattr(codes.values()[0], "code3"))
        self.assertFalse(hasattr(codes.values()[0], "code4"))

        # Check other properties
        self.assertTrue(hasattr(codes.values()[0], "uuid"))
        self.assertTrue(hasattr(codes.values()[0], "code_id"))
        self.assertFalse(hasattr(codes.values()[0], "parent"))

        # 2 roots
        self.assertEqual(2, len(filter(bool, [c.code1 for c in codes.values()])))

        # 3 'sub'roots
        self.assertEqual(3, len(filter(bool, [c.code2 for c in codes.values()])))

        # 2 'subsub'roots
        self.assertEqual(2, len(filter(bool, [c.code3 for c in codes.values()])))

    def test_parent(self):
        """Test parent format."""
        codes = self.export(structure="parent")
        self.assertTrue(hasattr(codes.values()[0], "parent"))

    def test_language(self):
        """Test if exporter renders correct labels"""
        codes = self.export(language=self.de)

        # Exporting structure format, thus no parent column
        self.assertFalse(hasattr(codes.values()[0], "parent"))

        # Should export DE codes
        de_code = codes[self.codes_list[0].id]
        self.assertIn("Ein", (de_code.code1, de_code.code2, de_code.code3))

        # Shouldn't export NL codes
        nl_code = codes[self.codes_list[1].id]
        self.assertNotIn("Een", (nl_code.code1, nl_code.code2, nl_code.code3))

    def test_labelcols(self):
        """Test whether extra labels are created """
        codes = self.export(labelcols=True)
        self.assertTrue(hasattr(codes.values()[0], "labelnl"))
        self.assertTrue(hasattr(codes.values()[0], "labelde"))
        self.assertFalse(hasattr(codes.values()[0], "label?"))

        nl_labels = filter(bool, [c.labelnl for c in codes.values()])
        self.assertEqual(1, len(nl_labels))
        self.assertEqual("Een", nl_labels[0])

        de_labels = filter(bool, [c.labelde for c in codes.values()])
        self.assertEqual(1, len(de_labels))
        self.assertEqual("Ein", de_labels[0])

        # Exporting structure format, thus no parent column
        self.assertFalse(hasattr(codes.values()[0], "parent"))

