from amcat.models.coding.serialiser import TextSerialiser, IntSerialiser, CodebookSerialiser, \
    BooleanSerialiser, QualitySerialiser
from amcat.tools import amcattest


class _DummyField(object):
    """Dummy coding schema field object with codebook"""

    def __init__(self, codebook):
        self.codebook = codebook
        self.codebook_id = codebook.id


class TestSerialiser(amcattest.AmCATTestCase):
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


    def test_booleanserialiser(self):
        """Test the boolean serialiser"""
        b = BooleanSerialiser(None)
        self.assertEqual(set(b.value_label(l) for l in b.possible_values), {'True', 'False'})
        self.assertEqual(b.serialise(True), 1)
        self.assertEqual(b.deserialise(1), True)
        self.assertEqual(b.serialise(False), 0)
        self.assertEqual(b.deserialise(0), False)

    def test_qualityserialiser(self):
        """Test the boolean serialiser"""
        b = QualitySerialiser(None)
        self.assertEqual(set(b.value_label(l) for l in b.possible_values),
                         {'-1.0', '-0.5', '0', '+0.5', '+1.0'})
        for x in b.possible_values:
            self.assertEqual(b.deserialise(b.serialise(x)), x)


    def test_codebookserialiser(self):
        """Test the codebook serialiser"""
        from amcat.models.language import Language

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

        self.assertEqual({c}, set(s.possible_values))

        self.assertEqual("bla", s.value_label(c))
        self.assertEqual("blx", s.value_label(c, l2))
