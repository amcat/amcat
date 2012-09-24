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
Auxilliary module for http/html based scraping
"""

import urllib, urllib2
from lxml import html
import logging; log = logging.getLogger(__name__)
import cookielib


HEADERS ={'User-agent': 'Mozilla/5.0 (X11; Linux i686; rv:6.0.2) Gecko/20100101 Firefox/6.0.2'}

class HTTPOpener(object):
    """Auxilliary class to help cookie-based opening and processing
    of web pages for scraping"""
    def __init__(self):
        cj = cookielib.MozillaCookieJar('mfp.cookies')
        self.cookiejar = urllib2.HTTPCookieProcessor(cj)
        self.opener = urllib2.build_opener(
            self.cookiejar,
            urllib2.HTTPRedirectHandler()
            )
        self.opener.addheaders = HEADERS.items()
        
    def getdoc(self, url, encoding=None):
        """Fetch a document from `url`. This method tries to determine the encoding of the document
        by looking at the HTTP headers. If those are missing, it leaves lxml to decide the
        encoding. 

        @param encoding: force an encoding (if not present in headers)
        @type encoding: instanceof basestring

        @param url: url to fetch
        """
        log.info('Retrieving "%s"' % urllib.unquote(url))
        response = self.opener.open(url)
        try:
            html_string = get_unicode(self.response, encoding)
        except: # decoding failed, use lxml default
            return html.parse(response).getroot()
        else: # decoding succeeded, use fromstring
            return html.fromstring(html_string)

ENCODING_HEADER = 'content-type'
ENCODING_KEY = 'charset'


def get_unicode(http_response, encoding=None):
    """Get the decoded unicode from response.
    Raises an exception if the encoding could not be found or applied
    """
    enc = encoding or get_encoding(http_response)
    return http_response.read().decode(enc)                        


def get_encoding(http_response):
    """Return charset (from HTTP-Headers). Raises an exception if no encoding could be found"""
    headers = http_response.getheaders() if hasattr(http_response, 'getheaders') else http_response.headers
    headers = dict((k.lower(),  v) for (k,v) in dict(headers).iteritems())
    if ENCODING_HEADER in headers:
        for kvpair in headers[ENCODING_HEADER].split(';'):
            if not "=" in kvpair: continue
            key, value = kvpair.split("=", 1)
            if key.strip() == ENCODING_KEY:
                return value.strip()
    raise ValueError("Could not find encoding in response with headers %s" % headers)


    

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestHTMLTools(amcattest.PolicyTestCase):
    # Sorry Internet, vanatteveldt.com has no encoding...
    TEST_SITES = {"http://amcat.vu.nl" : "utf-8", "http://vanatteveldt.com" : None}
    
    def test_encoding(self):
        """Does get_encoding give the correct encoding?"""
        for url, enc in self.TEST_SITES.items():
            response = urllib2.urlopen(url)
            if enc:
                self.assertEqual(get_encoding(response), "utf-8")
                self.assertEqual(type(get_unicode(response)), unicode)
            else:
                self.assertRaises(ValueError, get_encoding, response)
                self.assertRaises(ValueError, get_unicode, response)

    def test_getdoc(self):
        """Does the opener work on pages with and without encoding?"""
        o = HTTPOpener()
        for url in self.TEST_SITES:
            doc = o.getdoc(url)
            self.assertEqual(type(doc), html.HtmlElement)
        
