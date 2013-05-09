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
Plugin for uploading De Facto files (student edition) in HTML format
To use this plugin, choose to  'print' the articles and save the source
of the popup window as HTML. 
"""


from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload.defacto_prof import parse_meta, parse_ressort

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



class DeFactoStudent(UploadScript):
    
    def _get_units(self):
        html_bytes = self.options['file'].read()
        html = get_html(html_bytes)
        return split_html(html)
    

    def _scrape_unit(self, element):
        yield get_article(element)

def get_article(e):
    headline = get_headline(e)
    body = get_body(e)
    medium, date, page = get_meta(e)
    section = get_section(e)
    medium = get_or_create(Medium, name=medium)
    
    return Article(headline=headline, text=body, date=date, pagenr=page, section=section, medium=medium)

def get_html(html_bytes):
    parser = etree.HTMLParser()
    return etree.parse(StringIO(html_bytes), parser)
        
def split_html(html):   
    return html.xpath("//div[@class='eintrag']")

def get_meta(div):
    return parse_meta(div.find("pre").text)
    

def get_headline(div):
    return div.find("h3").text.strip()

def get_section(div):
    try:
        return parse_ressort(div.find("pre").text)
    except ValueError:
        return # no ressort?

def get_body(div):
    return "\n\n".join(stringify_children(p).strip() for p in div.findall("p")).strip()

if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)

    
def stringify_children(node):
    """http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml"""
    from lxml.etree import tostring
    from itertools import chain
    parts = ([node.text] +
            list(chain(*([c.text, tostring(c), c.tail] for c in node.getchildren()))) +
            [node.tail])
    # filter removes possible Nones in texts and tails
    return ''.join(filter(None, parts))



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import os.path, datetime
    
class TestDeFactoStudent(amcattest.PolicyTestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files', 'defacto')
        self.test1 = os.path.join(self.test_dir, 'DeFacto-Campus - Ausdruck1.htm')
        self.test1_html = get_html(open(self.test1).read())
        self.test2 = os.path.join(self.test_dir, 'DeFacto-Campus - Ausdruck2.htm')
        self.test2_html = get_html(open(self.test2).read())

    def test_split(self):
        elems = split_html(self.test1_html)
        self.assertEqual(len(elems), 21)

    def test_articles(self):
        arts = [get_article(x) for x in split_html(self.test1_html)]
        arts2 = [get_article(x) for x in split_html(self.test2_html)]
        self.assertEqual(arts2[-1].headline, 'Cafe Puls News 08:00 (08:00) - Peter Kaiser wird angelobt')
        self.assertEqual(arts2[-1].date, datetime.datetime(2013,4,2,8,0))
        
         
        
    def test_parse(self):
        elems = split_html(self.test1_html)

        self.assertEqual(get_meta(elems[0]), ("Der Standard", datetime.datetime(2013,4,2), 1))
        self.assertEqual(get_headline(elems[0]), u'SP und VP k\xf6nnten dritte Partei f\xfcr Koalition brauchen')        
        self.assertEqual(get_section(elems[0]), u'SEITE 1')
        body = get_body(elems[0])
        self.assertTrue(body.startswith(u'Wien - SP\xd6 und \xd6VP'))
        self.assertTrue(body.endswith("hoffen. (red) Seite 7"))
        self.assertEqual(len(body.split("\n\n")), 3) # no of paragraphs

        self.assertEqual(get_meta(elems[1]), ("Wiener Zeitung", datetime.datetime(2013,4,2), 3))
        self.assertEqual(get_headline(elems[1]), u'Politique autrichienne als Vorbild')
        self.assertEqual(get_section(elems[1]), 'Europa@welt')
        body = get_body(elems[1])
        self.assertTrue(body.startswith(u'Frankreichs Botschafter'))
        self.assertTrue(body.endswith("Treffen im Oktober 2012. epa"))
        self.assertEqual(len(body.split("\n\n")), 28) # no of paragraphs

        body = get_body(elems[-1])
        self.assertTrue('<a href="mailto:peter.filzmaier@donau-uni.ac.at">peter.filzmaier@donau-uni.ac.at</a>' in body)
