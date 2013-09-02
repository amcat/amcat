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

import logging; log = logging.getLogger(__name__)

import csv, collections
from lxml import etree
from lxml.etree import Element 

from django import forms
from django.forms import widgets

from amcat.models import Code, Codebook, Language
from amcat.scripts.script import Script

def _create_element(tag, value):
    el = Element(tag)
    el.text = unicode(value)
    return el

def _node_to_xml(treeitem):
    code = Element("code")
    code.append(_create_element("id", unicode(treeitem.code_id)))
    code.append(_create_element("label", unicode(treeitem.label)))

    children = Element("children")
    for child in treeitem.children:
        children.append(_node_to_xml(child))

    code.append(children)
    return code

def codebook_to_xml(codebook):
    codebook.cache_labels()

    # Create Codebook element and add its properties
    xml_root = Element("codebook")
    xml_root.append(_create_element("id", unicode(codebook.id)))
    xml_root.append(_create_element("project_id", unicode(codebook.project_id)))
    xml_root.append(_create_element("name", codebook.name))

    # Get roots of codebook and add them
    roots = Element("roots")
    for root in codebook.get_tree():
        roots.append(_node_to_xml(root))

    xml_root.append(roots)
    return xml_root

class ExportCodebookAsXML(Script):
    """Export a codebook to an xml file."""

    class options_form(forms.Form):
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all())
        
    def _run(self, codebook, **kargs):
        return etree.tostring(codebook_to_xml(codebook))

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
from amcat.tools import amcattest

class TestExportCodebookAsXML(amcattest.PolicyTestCase):
    def test_codebook_to_xml(self):
        # Empty codebook
        cb = codebook_to_xml(amcattest.create_test_codebook())

        self.assertEquals(cb.tag, "codebook")
        children = [c.tag for c in cb.iterchildren()]

        for prop in ("project_id", "name", "roots", "id"):
            self.assertTrue(prop in children)

        self.assertFalse(len([c for c in cb.find("roots")]))

        # Codebook with two roots
        cb = codebook_to_xml(amcattest.create_test_codebook_with_codes()[0])
        self.assertEquals([c.find("label").text for c in cb.find("roots")], ["A", "B"])
        self.assertTrue("A1a" in etree.tostring(cb))

        # Test unicode
        cb = amcattest.create_test_codebook_with_codes()[0]
        label = cb.codes[0].labels.all()[0]
        label.label = u"\u2603" # It's Mr. Snowman!
        label.save()

        # Shouldn't raise errors
        cb = codebook_to_xml(Codebook.objects.get(id=cb.id))
        etree.tostring(cb)


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

