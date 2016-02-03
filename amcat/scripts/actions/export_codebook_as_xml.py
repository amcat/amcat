#!/usr/bin/python
# ##########################################################################
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

import logging;

log = logging.getLogger(__name__)

from lxml import etree
from lxml.etree import Element

from django import forms

from amcat.models import Codebook
from amcat.scripts.script import Script


def _create_element(tag, value):
    el = Element(tag)
    el.text = str(value)
    return el


def _node_to_xml(treeitem):
    code = Element("code")
    code.append(_create_element("id", str(treeitem.code_id)))
    code.append(_create_element("label", str(treeitem.label)))

    children = Element("children")
    for child in treeitem.children:
        children.append(_node_to_xml(child))

    code.append(children)
    return code


def codebook_to_xml(codebook):
    codebook.cache_labels()

    # Create Codebook element and add its properties
    xml_root = Element("codebook")
    xml_root.append(_create_element("id", str(codebook.id)))
    xml_root.append(_create_element("project_id", str(codebook.project_id)))
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


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    cli.run_cli()

