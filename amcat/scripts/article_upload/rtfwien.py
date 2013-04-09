#! /usr/bin/python
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
Plugin for uploading RTF files from Wien (need better name)
"""


from amcat.scripts.article_upload.upload import UploadScript

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools.djangotoolkit import get_or_create
from amcat.tools import toolkit

from cStringIO import StringIO
import subprocess
from tempfile import NamedTemporaryFile, mkstemp
from lxml import etree
import re
import os
import sys
from amcat.tools.toolkit import readDate

class RTFWien(UploadScript):

    
    def _get_units(self):
        xml = get_xml(self.options['file'].read())
        return split_xml(xml)
    

    def _scrape_unit(self, element):
        yield get_article(element)

def get_article(e):
    headline = get_headline(e)
    body = get_body(e)
    medium, date, page = get_meta(e)
    section = get_section(e)
    medium = get_or_create(Medium, name=medium)
    
    return Article(headline=headline, text=body, date=date, pagenr=page, section=section, medium=medium)

    
def siblings_until_stop(elem, stop):
    for sibling in elem.xpath("following-sibling::*"):
        if sibling == stop:
            break
        yield sibling
        

def split_xml(xml):
    breaks = xml.xpath("//page-break")

    # elements are para - table - *para*

    # yield until first break; between two breaks; after last break
    yield breaks[0].xpath("preceding-sibling::*")[2]
    for brk, nxt in zip(breaks[:-1], breaks[1:]):
        yield tuple(siblings_until_stop(brk, nxt))[2]
    yield breaks[-1].xpath("following-sibling::*")[2]
    
        

def get_headline(e):
    hl = e.xpath("descendant-or-self::paragraph-definition[@style-number='s0004']//inline[@bold='true']")
    for x in hl:
        if x.text.strip():
            return x.text.strip()

def get_body(e):
    pars = e.xpath("descendant-or-self::paragraph-definition[@style-number='s0004']/para[inline/@bold='true']"
                   "/following-sibling::*")
    text = []
    for par in pars:
        lines = par.xpath("./inline")
        if lines:
            text.append("\n".join((l.text or '') for l in lines))
            text.append("\n")
        else:
            text.append("\n\n")
    return "".join(text).strip()


def get_date(e):
    for par in e.xpath("descendant-or-self::paragraph-definition[@style-number='s0003']//inline[@bold='true']"):
        if par.text.strip():
            return toolkit.readDate(par.text)
            
def get_section(e):
    for par in e.xpath("descendant-or-self::paragraph-definition[@style-number='s0004']//inline[@italics='true']"):
        m = re.search("Ressort:(.*)", par.text)
        if m:
            return m.group(1).strip()

            
            
def get_meta(e):
    for par in e.xpath("descendant-or-self::paragraph-definition[@style-number='s0004']//inline[@italics='true']"):
        m = re.match(r"(.*?) vom (\d\d\.\d\d\.\d\d\d\d)( \d\d[.:]\d\d\b)?(.*)", par.text)
        medium, date, time, pagestr= m.groups()
        if time:
            date = date + time.replace(".", ":")
        date = toolkit.readDate(date)
        m = re.search("Seite:? (\d+)", pagestr)
        if m:
            page = int(m.group(1))
        else:
            page = None
        return medium, date, page
            
def get_xml(text):
    with NamedTemporaryFile() as f:
        f.write(text)
        f.flush()
        try:
            xml = subprocess.check_output(["rtf2xml", f.name])
        except Exception, e:
            f, fn = mkstemp(suffix=".rtf")
            os.write(f, text)
            raise Exception("Error on calling rtf2xml, is rtf2xml installed? RTF saved to {fn}\n(use 'sudo pip install rtf2xml' to install)\n {e}".format(**locals()))
    return parse_xml(xml)

def parse_xml(xml_bytes):
    xml_bytes = xml_bytes.replace(' xmlns="http://rtf2xml.sourceforge.net/"', '')
    xml_bytes = xml_bytes.replace(' encoding="us-ascii"?>', ' encoding="utf-8"?>')
    return etree.fromstring(xml_bytes)
    
if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import os.path, datetime
    
class TestRTFWien(amcattest.PolicyTestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files', 'rtfwien')
        self.test_prof_xml = os.path.join(self.test_dir, 'rtf_prof.xml')

    def _get_prof_docs(self):
        xml = parse_xml(open(self.test_prof_xml).read())
        return list(split_xml(xml))
        
        

    def test_get_headline(self):
        chunks = self._get_prof_docs()
        self.assertEqual(get_headline(chunks[0]), "Zeit im Bild 1 (19:30) - Streit um Mandate bei der FPK")
        self.assertEqual(get_headline(chunks[23]), 'EPROFIL Seite 83')
        self.assertEqual(get_headline(chunks[-1]), 'OREICHP Sonntag Seite 8')

    def test_get_body(self):
        chunks = self._get_prof_docs()
        b = get_body(chunks[23])
        self.assertTrue(b.startswith('Per cocer sardelle'))
        self.assertTrue(b.endswith('rz 2013 profil 12 83'))
        
    def test_prof_articles(self):
        chunks = self._get_prof_docs()
        # do we get the right number of chunks?
        self.assertEqual(len(chunks), 43)
        arts = map(get_article, chunks)
        
        # is the first article ok?
        a = arts[0]
        self.assertEqual(a.headline, "Zeit im Bild 1 (19:30) - Streit um Mandate bei der FPK")
        self.assertEqual(str(a.medium), "Zeit im Bild 1")
        self.assertEqual(a.date, datetime.datetime(2013, 3, 17, 19, 30))

        
