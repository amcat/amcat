#!/usr/bin/python

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

import logging;
from amcat.tools import amcattest
from amcat.tools.amcattest import AmCATTestCase

log = logging.getLogger(__name__)

import collections

from django import forms

from amcat.scripts.script import Script
from amcat.models import Codebook, Language
from amcat.tools.table import table3

LABEL_PREFIX = "label - "


TreeRow = collections.namedtuple("TreeRow", ["indent", "code"])

class TreeCodeColumn(table3.ObjectColumn):
    def __init__(self, i, language):
        super(TreeCodeColumn, self).__init__(label="code-{n}".format(n=i+1))
        self.i = i
        self.language = language

    def getCell(self, row):
        if row.indent == self.i:
            return row.code.get_label(self.language)


class CodeColumn(table3.ObjectColumn):
    def __init__(self, label, attr, language):
        super(CodeColumn, self).__init__(label=label)
        self.attr = attr
        self.language = language

    def getCell(self, row):
        return getattr(row, self.attr).get_label(self.language, fallback=False)

            
class ExportCodebook(Script):
    """
    Export a codebook to a table (csv file).

    Structure is indicated depending on the 'structure' parameter:
    - 'indented' creates a series of columns code-1 .. code-n with indentation
    - 'parent' creates two columns 'code' and 'parent', giving the parent for each code

    Next to these columns, the table will contain codeid and uuid columns
    """

    class options_form(forms.Form):
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all())
        structure = forms.ChoiceField(choices = [(s, s.title()) for s in ['indented', 'parent']])
        language = forms.ModelChoiceField(queryset=Language.objects.all(),
                                          help_text="Defatul language for labels")
        labelcols = forms.BooleanField(label="Label columns", required=False,
                                       help_text="Export extra columns for other labels")
        
    def _run(self, codebook, structure, language, labelcols, **kargs):
        codebook.cache_labels()
        method = {"indented": self.tree_table, "parent": self.parent_table}[structure]
        return method(codebook, language, labelcols)

    def add_label_columns(self, table):
        if self.options['labelcols']:
            cb = self.options['codebook']
            deflang = self.options['language']
            langs = set(Language.objects.filter(labels__code__codebook_codes__codebook=cb).distinct())
            langs -= {deflang}
            for lang in langs:
                table.addColumn(CodeColumn("label - {lang}".format(**locals()), "code", lang))

    def tree_table(self, codebook, language, labelcols):
        rows = list(_get_tree(codebook))

        result = table3.ObjectTable(rows=rows)
        result.addColumn(lambda row : row.code.uuid, label="uuid")
        result.addColumn(lambda row : row.code.id, label="code_id")
        self.add_label_columns(result)
        depth = max(row.indent for row in rows) + 1
        for i in range(depth):
            result.addColumn(TreeCodeColumn(i, language))

        return result

    def parent_table(self, codebook, language, labelcols):
        result = table3.ObjectTable(rows=codebook.codebookcodes)
        result.addColumn(lambda row: row.code.uuid, label="uuid")
        result.addColumn(lambda row: row.code.id, label="code_id")
        result.addColumn(lambda row: row.code.get_label(language), label="label")
        result.addColumn(lambda row: getattr(row.parent, "id", None), label="parent")
        self.add_label_columns(result)
        return result

        
def _get_tree(codebook):
    parents = {cc.code : cc.parent for cc in codebook.codebookcodes}
    for root in (code for (code, parent) in parents.iteritems() if parent is None):
        for row in _get_tree_rows(parents, 0, root):
            yield row


def _get_tree_rows(parents, indent, parent):
    yield TreeRow(indent, parent)
    for child in (c for (c, p) in parents.iteritems() if p == parent):
        for row in _get_tree_rows(parents, indent+1, child):
            yield row


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

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    #cli.run_cli().to_csv(stream=sys.stdout)
    print cli.run_cli().to_csv()
    #print result.output()

