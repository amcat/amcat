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
from amcat.models import CodingSchemaFieldType, CodingSchemaField
from amcat.models.coding import serialiser
from amcat.tools import amcattest


class TestCodingSchemaFieldType(amcattest.AmCATTestCase):
    def test_get_serialiser(self):
        """Are the built in field types present and bound to the right class?"""
        fieldtype = CodingSchemaFieldType.objects.get(pk=1)
        self.assertEqual(fieldtype.serialiserclass, serialiser.TextSerialiser)


class TestCodingSchemaField(amcattest.AmCATTestCase):
    def test_create_field(self):
        """Can we create a schema field object on a schema"""
        fieldtype = CodingSchemaFieldType.objects.get(pk=1)
        a = amcattest.create_test_schema()
        f = CodingSchemaField.objects.create(codingschema=a, fieldnr=1, fieldtype=fieldtype)
        self.assertIsNotNone(f)