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

"""
(De)Serialisation support for annotation values

Annotation Values need to be serialised and deserialised based on the
schema field that they are an annotation of.

Definitions:
Serialised Value: a primitive type (currently: str or int)
Deserialised Value: a domain object, possibly a django Model instance

"""

import logging; log = logging.getLogger(__name__)

class BaseSerialiser(object):
    """Base class for serialisation support for schema fields"""
    def __init__(self, field, deserialised_type=str, serialised_type=str):
        self.field = field
        self.deserialised_type = deserialised_type
        self.serialised_type = serialised_type
    def deserialise(self, value):
        """Convert the given serialised value to a domain object"""
        return self.deserialised_type(value)
    def serialise(self, value):
        """Convert the given domain object to a serialised value"""
        return self.serialised_type(value)

class TextSerialiser(BaseSerialiser):
    """Simple str - str serialiser"""
    def __init__(self, field):
        super(TextSerialiser, self).__init__(field, str, str)

class IntSerialiser(BaseSerialiser):
    """Simple int - int serialiser"""
    def __init__(self, field):
        super(IntSerialiser, self).__init__(field, int, int)




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestSerialiser(amcattest.PolicyTestCase):
    def test_textserialiser(self):
        """Test the str serialiser"""
        t = TextSerialiser(None)
        self.assertEqual(t.deserialise(12), '12')
        self.assertEqual(t.serialise('abc'), 'abc')
    def test_intserialiser(self):
        """Test the int serialiser"""
        t = IntSerialiser(None)
        self.assertEqual(t.deserialise(12), 12)
        self.assertEqual(t.serialise('-99'), -99)
        self.assertRaises(ValueError, t.serialise, 'abc')
