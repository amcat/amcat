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
"""Document objects returned by various scraping-functions."""

from amcat.scraping.toolkit import dictionary
from amcat.contrib.html2text import html2text

from lxml import html
from lxml import etree

try:
    # Python 3.x
    from html import parser
except ImportError:
    import HTMLParser as parser

import copy
import types

import logging; log = logging.getLogger(__name__)



_ARTICLE_PROPS = [
    'date', 'section', 'pagenr', 'headline', 'byline', 'length',
    'url', 'externalid', 'text', 'parent', 'medium', 'author'
]
class Properties(object):
    pass

class Document(object):
    """Object representing an document. No properties are
    forced upon constructing. This is the base for all other
    objects.

    __getattr__ and __setattr__ will raise errors when not
    initialized."""
    def __init__(self, parent=None, **kargs):
        """@param parent: """
        self.props = Properties()
        self.parent = parent
        self.id = None

        for k,v in kargs.items():
            setattr(self.props, k, v)

    def getprops(self):
        return self.props.__dict__

    def updateprops(self, dic):
        """Update properties.

        @type dic: dictionary
        @param dic: dictionary to use to update the properties"""
        self.props.__dict__.update(dic)

    def copy(self, cls=None, parent=None):
        """Returns a copy of itself, with all the properties deep-copied."""
        parent = parent or self.parent
        cls = cls or Document

        return cls(parent=parent, **copy.deepcopy(self.getprops()))

    def prepare(self, processor, force=False):
        """This method prepares the document for processing. See HTMLDocument for
        sample usage."""
        pass

    def create_article(self, doc):
        """Convert the document object into an article"""
        art = Article()

        # All properties in _ARTICLES_PROPS are set on a new Article,
        # else in Article.metastring.
        _metastring = dict()
        for prop, value in doc.getprops().items():
            if prop in _ARTICLE_PROPS:
                setattr(art, prop, value)
            else:
                _metastring[prop] = value

        art.metastring = str(_metastring)
        return art

class HTMLDocument(Document):
    """Document object for HTML documents. This means that all properties are converted to
    MarkDown compatible text in `getprops`. Moreover, lxml.html objects (or even lists of
    lxml.html objects) are converted to text before returning."""
    def __init__(self, doc=None, *args, **kargs):
        self.doc = doc # lxml object
        super(HTMLDocument, self).__init__(*args, **kargs)

    def _convert(self, val):
        t = type(val)

        if t is str:
            return val.strip()

        if t in (html.HtmlElement, etree._Element):
            #return html2text(html.tostring(val)).strip()
            try:
                return html2text(html.tostring(val)).strip() #encoding=str
            except (parser.HTMLParseError, TypeError) as e:
                print('Warning: html2text failed!')
                return 'Converting from HTML failed!'

        if t in (list, tuple, types.GeneratorType):
            """Check if all objects in list are HtmlElement and then proceed"""
            val = tuple(val)

            if all([type(e) in (html.HtmlElement, etree._Element) for e in val]):
                return "\n\n".join(map(self._convert, val))            

        # Unknown type
        return val

    def copy(self, parent=None):
        d = super(HTMLDocument, self).copy(cls=HTMLDocument, parent=parent)
        d.doc = self.doc
        return d

    @dictionary
    def getprops(self):
        """Return properties converted (where applicable) to MarkDown"""
        for k,v in super(HTMLDocument, self).getprops().items():
            yield (k, self._convert(v))

    def prepare(self, processor, force=False):
        print "XXXXXXXXXXXXXXXXXXX"
        log.info("Preparing %s using processor %s, getdoc=%s" % (getattr(self.props, "url", None),
                                                                 processor, getattr(processor, "getdoc", None)))
        if (self.doc is None or force):
            try:
                self.doc = processor.getdoc(self.props.url)
            except AttributeError:
                                                                     
                pass # no need to prepare if opener or url not known


class IndexDocument(HTMLDocument):
    """
    Represents an index-page of a newspaper.
    """
    def __init__(self, page=None, **kargs):
        self.children = []
        self.page = page
        
        super(IndexDocument, self).__init__(**kargs)

    def addchild(self, child):
        self.children.append(child)

    def getprops(self):
        committed = [(child.id is not None) for child in self.children]
        if not all(committed):
            raise(ValueError("Please yield the index-page *after* all children."))

        if not all([hasattr(child, 'coords') for child in self.children]):
            raise(ValueError("Make sure all index-children have an attribute 'coords'."))

        # Children seem to be valid.
        if self.page is None:
            raise(ValueError("self.page of IndexDocument cannot be None when committing."))

        headline = '[INDEX] page %s' % self.page
        text = ['[IMAGEMAP-1]',]

        for child in self.children:
            for coord in child.coords:
                coord = ", ".join(map(str, coord))
                text.append("[%s -> %s]" % (coord, child.id))

        return dict(headline=headline, text="\n".join(text),
                    page=self.page, **self.props.__dict__)



    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestDocument(amcattest.PolicyTestCase):
    def test_set_get(self):
        doc = Document()

        doc.foo = 'bar'

        print(doc.getprops())
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

        self.assertEqual(doc.spam, 'ham')
        doc_b = doc.copy()
        self.assertFalse(doc_b.getprops() is doc.getprops())
        self.assertEqual(doc_b.spam, 'ham')
        self.assertTrue(doc_b.foo == doc.foo)
        self.assertFalse(doc_b.foo is doc.foo)

