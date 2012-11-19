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

from cStringIO import StringIO
import subprocess
from tempfile import NamedTemporaryFile, mkstemp
from lxml import etree
import re
import os
import sys
from amcat.tools.toolkit import readDate

class RTFWien(UploadScript):
    
    def split_text(self, text):
        for t in  text.split("\n\page "):
            # convert fragment to standalone rtf
            if not t.startswith("{\\rtf1"):
                t = "{\\rtf1" + t
            if not t.strip().endswith("}"):
                if t.strip().endswith("\\"):
                    t = t.strip()[:-1]
                t = t + " }"
            yield t
            
    def parse_document(self, text):
        xml = self.get_xml(text)
        try:
            return self.get_article(xml)
        except:
            f, fn = mkstemp(suffix=".rtf")
            os.write(f, text)
            f, fn2 = mkstemp(suffix=".xml")
            os.write(f, etree.tostring(xml, pretty_print=True))
            print >>sys.stderr, "Error on parsing, rtf wrtten to %s, xml written to %s" % (fn, fn2)
            raise

    def get_xml(self, text):
        with NamedTemporaryFile() as f:
            f.write(text)
            f.flush()
            xml = subprocess.check_output(["rtf2xml", f.name])
            xml = xml.replace(' xmlns="http://rtf2xml.sourceforge.net/"', '')
            return etree.fromstring(xml)

    def get_article(self, xml):
        headline, body = self.get_headline_body(xml)
        medium, date, page = self.get_mediumdate(xml)
        section = self.get_section(xml)
        url = self.get_url(xml)
        medium = get_or_create(Medium, name=medium)
        return Article(headline=headline, text=body, date=date, pagenr=page, section=section, url=url, medium=medium)

    def get_headline_body(self, xml):
        # headline has size 12
        hl = xml.xpath("//paragraph-definition[@style-number='s0001']//inline[@font-size='12.00']")
        hls = [h.text.strip() for h in hl if h.text.strip()]
        if len(hls) != 1:
            raise Exception("Cannot parse headlines %r" % hls)
        headline = hls[0]

        # body are the paragraphs (inlines) following the headline
        body = [[]]
        for p in hl[0].xpath("following-sibling::*"):
            line = p.text.replace("\u2028", "")
            if not line.strip(): continue
            m = re.match(" {3,}[A-Z]", line) # indentation to start new paragraph
            if m and body[-1]: body.append([])
            body[-1].append(line)
        body = "\n\n".join(re.sub("\s+", " ", " ".join(lines)).strip()
                           for lines in body)
        return headline, body
    
    def get_mediumdate(self, xml):
        # look for a table with a <row><cell>Quelle:</cell><cell>"Der standard" vom DATE  Seite: PAGE</cell>
        for line in xml.xpath("//table//inline[text()='Quelle:']/ancestor::cell/following-sibling::cell//inline"):
            line = line.text
            m = re.match('"([\w ]+)" vom ([\d\.]+)\s+Seite: (\d+)', line)
            if m:
                source, date, page = m.groups()
                date = readDate(date)
                page = int(page)
                return source, date, page
        raise Exception("Cannot find/interpret Quelle")

    def get_section(self, xml):
        # look for a table with a <row><cell>Ressort:</cell><cell>RESSORT</cell>
        for line in xml.xpath("//table//inline[text()='Ressort:']/ancestor::cell/following-sibling::cell//inline"):
            line = line.text.strip()
            if line:
                return line
        raise Exception("Cannot find/interpret Ressort")
        
    def get_url(self, xml):
        # find url under 'dauerhafte adresse'
        for line in xml.xpath("//paragraph-definition[@style-number='s0003']"
                              "//inline[text()='Dauerhafte Adresse des Dokuments:']/following-sibling::*"):
            line = line.text.strip()
            if line.startswith("http"):
                return line
        raise Exception("Cannot get url")
    
if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import os.path
    
class TestRTFWien(amcattest.PolicyTestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files', 'rtfwien')
        self.test1 = os.path.join(self.test_dir, 'test1.rtf')
        self.test2 = os.path.join(self.test_dir, 'test2.rtf')
        self.test1_text = open(self.test1).read().decode("utf-8")
        self.test2_text = open(self.test2).read().decode("utf-8")
        self.script = RTFWien(project=amcattest.create_test_project().id)
    
    def test_split(self):
        for (txt, n) in [
            (self.test1_text, 25),
            (self.test2_text, 407)]:
            articles = RTFWien(project=amcattest.create_test_project().id).split_text(txt)
            self.assertEqual(len(articles), n)
            
    def test_get_xml(self):
        fragments = self.script.split_text(self.test1_text)
        for fragment in fragments:
            xml = self.script.get_xml(fragment)
            return

    def test_get_article(self):
        fragments = self.script.split_text(self.test1_text)
        for i, headline, medium, page in [
            (0, "KOPF DES TAGES", "Der Standard", 40),
            ]:
            
            fragment = fragments[i]
            xml = self.script.get_xml(fragment)
            a = self.script.get_article(xml)
            self.assertEqual(a.headline, headline)
            self.assertEqual(a.medium.name, medium)
            self.assertEqual(a.pagenr, page)
            
