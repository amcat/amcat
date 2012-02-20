import unittest

from amcat.tools.scraping.objects import Document, HTMLDocument

class DocumentTest(unittest.TestCase):
    def test_set_get(self):
        doc = Document()

        doc.foo = 'bar'

        self.assertEqual(doc.foo, 'bar')
        self.assertEqual(doc.getprops()['foo'], 'bar')

    def test_del(self):
        doc = Document()

        doc.foo = 'bar'; del doc.foo
        self.assertRaises(AttributeError, lambda: doc.foo)

        def delete(): del doc.foo
        self.assertRaises(AttributeError, delete)

    def test_updateprops(self):
        doc = Document()

        dic = dict(a='b', b='c')
        doc.updateprops(dic)

        self.assertEqual(dic, doc.getprops())
        self.assertNotEqual({}, doc.getprops())


    def test_return_types(self):
        doc = Document()

        self.assertEqual(dict, type(doc.getprops()))

    def test_copy(self):
        doc = Document()

        doc.foo = ['bar', 'list']
        doc.spam = 'ham'

        doc_b = doc.copy()
        self.assertFalse(doc_b.getprops() is doc.getprops())
        self.assertEqual(doc_b.spam, 'ham')
        self.assertTrue(doc_b.foo == doc.foo)
        self.assertFalse(doc_b.foo is doc.foo)

class HTMLDocumentTest(unittest.TestCase):
    pass



if __name__ == '__main__':
    unittest.main()
