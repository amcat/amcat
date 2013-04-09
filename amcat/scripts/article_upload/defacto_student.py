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

class DeFactoStudent(UploadScript):
    
    def _get_units(self):
        html_bytes(self.options['file'].read())
        html = get_html(html_bytes)
        return split_html(html)
    

    def _scrape_unit(self, element):
        yield get_article(element)


def get_html(html_bytes):
    parser = etree.HTMLParser()
    return etree.parse(StringIO(html_bytes), parser)
        
def split_html(html):
    
    return html.xpath("//div[@class='eintrag']")
    
if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli(handle_output=False)




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import os.path, datetime
    
class TestDeFactoStudent(amcattest.PolicyTestCase):

    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), 'test_files', 'rtfwien')
        self.test1 = os.path.join(self.test_dir, 'DeFacto-Campus - Ausdruck1.htm')
        self.test1_html = get_html(open(self.test1).read())

    def test_split(self):
        elems = split_html(self.test1_html)
        print elems
