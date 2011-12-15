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
(De)Serialisation support for coding values

Coding Values need to be serialised and deserialised based on the
schema field that they are an coding of.

Definitions:
Serialised Value: a primitive type (currently: str or int)
Deserialised Value: a domain object, possibly a django Model instance

"""

import logging; log = logging.getLogger(__name__)

from amcat.model.coding.code import Code
from amcat.model.coding.codebook import get_codebook

class BaseSerialiser(object):
    """Base class for serialisation support for schema fields"""
    def __init__(self, field, deserialised_type=str, serialised_type=str):
        self.field = field
        self.deserialised_type = deserialised_type
        self.serialised_type = serialised_type
    def deserialise(self, value):
        """Convert the given serialised value to a domain object

        @param value: The value to be deserialized, which should be of type self.serialized_type
        @return: a value of type self.deserialized_Type. Raises an error if value could not
                 be deserialized
        """
        if value is None: return None
        return self.deserialised_type(value)
    def serialise(self, value):
        """Convert the given domain object to a serialised value

        @param value: The value to be serialized, which should be of type self.deserialized_type
        @return: a value of type self.serialized_Type. Raises an error if value could not
                 be serialized
        """
        if value is None: return None
        return self.serialised_type(value)
    @property
    def possible_values(self):
        """Get the possible values

        @return: a sequence of (deserialised) values
                 or None if this serialiser in not for a 'drop down' field
        """
        return None

    def value_description(self, value, language=None):
        """Get a description for the given (desrialised) value

        @param language: an optional preferred language, which may be ignored
        """
        return unicode(value)
    
    def value_label(self, value, language=None):
        """Get a label for the given (deserialised) value

        @param language: an optional preferred language, which may be ignored
        """
        return unicode(value)
    
class TextSerialiser(BaseSerialiser):
    """Simple str - str serialiser"""
    def __init__(self, field):
        super(TextSerialiser, self).__init__(field, str, str)

class IntSerialiser(BaseSerialiser):
    """Simple int - int serialiser"""
    def __init__(self, field):
        super(IntSerialiser, self).__init__(field, int, int)


_memo = {}
def CodebookSerialiser(field):
    """Retrieve/Create a memoized codebooksereialiser for the given field.codebook"""
    # no harm if threads access concurrently, so no need to use local store or mutex
    # limited total no of codebooks, so no harm in memoising all of them
    # or should we memoise on codebook level, ie have a general codebook factory?
    codebookid = field.codebook_id
    try:
        return _memo[codebookid]
    except KeyError:
        _memo[codebookid] = _CodebookSerialiser(field)
        return  _memo[codebookid]
        
class _CodebookSerialiser(BaseSerialiser):
    """int - amcat.model.coding.Code serialiser"""
    def __init__(self, field):
        super(_CodebookSerialiser, self).__init__(field, Code, int)
        self.codebook = get_codebook(field.codebook_id)
        
    def deserialise(self, value):
        try:
            return self.codebook.get_code(value)
        except ValueError:
            # code was removed from codebook
            return Code.objects.get(pk=value)
            
    def serialise(self, value):
        if value is None: return None
        return value.id
    
    @property
    def possible_values(self):
        return self.codebook.codes

    def value_description(self, value, language=None):
        return unicode(value)
    
    def value_label(self, value, language=None):
        return value.get_label(language)

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class _DummyField(object):
    """Dummy coding schema field object with codebook"""
    def __init__(self, codebook):
        self.codebook = codebook
        self.codebook_id = codebook.id

class TestSerialiser(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = ["W0613"] # unused argument on virtual method
    def test_textserialiser(self):
        """Test the str serialiser"""
        t = TextSerialiser(None)
        self.assertEqual(t.deserialise(12), '12')
        self.assertEqual(t.serialise('abc'), 'abc')
        self.assertIsNone(t.possible_values)
    def test_intserialiser(self):
        """Test the int serialiser"""
        t = IntSerialiser(None)
        self.assertEqual(t.deserialise(12), 12)
        self.assertEqual(t.serialise('-99'), -99)
        self.assertRaises(ValueError, t.serialise, 'abc')
        self.assertIsNone(t.possible_values)
        
    def test_codebookserialiser_memoisation(self):
        """Does memoisation work?"""
        A = amcattest.create_test_codebook(name="A")
        B = amcattest.create_test_codebook(name="B")
        s1 = CodebookSerialiser(_DummyField(A))
        s2 = CodebookSerialiser(_DummyField(A))
        self.assertIs(s1, s2)
        s3 = CodebookSerialiser(_DummyField(B))
        self.assertNotEqual(s2, s3)
        
    
    def test_codebookserialiser(self):
        """Test the codebook serialiser"""
        from amcat.model.language import Language
        A = amcattest.create_test_codebook(name="A")
        c = amcattest.create_test_code(label="bla")

        l2 = Language.objects.create(label="XXX")
        c.add_label(language=l2, label="blx")

        A.add_code(c)
        s = CodebookSerialiser(_DummyField(A))
        self.assertEqual(s.serialise(c), c.id)
        self.assertEqual(s.deserialise(c.id), c)
        d = amcattest.create_test_code(label="not in codebook")
        #(de)serialising a code from outside codebook should not raise errors:

        self.assertEqual(s.serialise(d), d.id)
        self.assertEqual(s.deserialise(d.id), d)

        self.assertRaises(Exception, s.deserialise, -9999999999999999)
        
        self.assertEqual([c], s.possible_values)
        
        self.assertEqual("bla", s.value_label(c))
        self.assertEqual("blx", s.value_label(c, l2))
        
