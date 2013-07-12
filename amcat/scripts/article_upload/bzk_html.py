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
Plugin for uploading html files of a certain markup, provided by BZK
"""

from __future__ import unicode_literals, absolute_import
from amcat.scripts.article_upload.upload import UploadScript
from amcat.scraping.document import HTMLDocument
from amcat.tools.toolkit import readDate
from amcat.models.medium import Medium
from lxml import html
import re
import logging; log = logging.getLogger(__name__)
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES as MEDIUM_ALIASES

class BZK(UploadScript):
    def _scrape_unit(self, _file):
        if type(_file) == unicode: #command line
            etree = html.fromstring(_file)
        else: #web interface
            try:
                etree = html.parse(_file).getroot()
            except IOError as e:
                log.exception("Failed html.parse")
                raise TypeError("failed HTML parsing. Are you sure you've inserted the right file?\n{e}".format(**locals()))

        title = etree.cssselect("title")[0].text.lower().strip()
        if "intranet/rss" in title or "werkmap" in title:
            for article in self.scrape_file(etree, title):
                yield article
        else:
            raise ValueError("Supports only 'werkmap' and 'intranet/rss' documents")
        
    def scrape_file(self, _html, t):
        if "werkmap" in t:
            divs = _html.cssselect("#articleTable div")
        elif "intranet/rss" in t:
            divs = [div for div in _html.cssselect("#sort div") if "sort_" in div.get('id')]
            
        for div in divs:
            article = HTMLDocument()
            article.props.html = div
            article.props.headline = div.cssselect("#articleTitle")[0].text_content()
            article.props.text = div.cssselect("#articleIntro")[0]
            articlepage = div.cssselect("#articlePage")
            if articlepage:
                article.props.pagenr, article.props.section = self.get_pagenum(articlepage[0].text)

            if not div.cssselect("#sourceTitle")[0].text:
                article.props.medium = Medium.get_or_create("unknown medium")
            else:
                article.props.medium = Medium.get_or_create(div.cssselect("#sourceTitle")[0].text)
            date_str = div.cssselect("#articleDate")[0].text
            try:
                article.props.date = readDate(date_str)
            except ValueError:
                log.error("parsing date \"{date_str}\" failed".format(**locals()))
            else:
                yield article

    def create_medium(self, html):
        if not html.text:
            medium = "unknown"
        else:
            medium = html.text
        if medium in MEDIUM_ALIASES.keys():
            return Medium.get_or_create(MEDIUM_ALIASES[medium])
        else:
            return Medium.get_or_create(medium)

    def get_pagenum(self, text):
        p = re.compile("pagina ([0-9]+)([,\-][0-9]+)?([a-zA-Z0-9 ]+)?")
        m = p.search(text.strip())
        pagenum, otherpage, section = m.groups()
        if section:
            section = section.strip()
        return int(pagenum), section


if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(BZK)
        
        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestBZK(amcattest.PolicyTestCase):
    def setUp(self):
        from django.core.files import File
        import os.path, json
        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.bzk = BZK(project = amcattest.create_test_project().id,
                  file = File(open(os.path.join(self.dir, 'test.html'))),
                  articleset = amcattest.create_test_set().id)
        self.result = self.bzk.run()

        def test_scrape_unit(self):
            self.assertTrue(self.result)
        
        def test_scrape_file(self):
            #props to check for:
            # headline, text, pagenr, section, medium, date
            must_props = ('headline', 'text', 'medium', 'date')
            may_props = ('pagenr','section')
            must_props = [[getattr(a.props, prop) for a in self.result] for prop in must_props]
            may_props = [[getattr(a.props, prop) for a in self.result] for prop in may_props]

            for proplist in must_props:
                self.assertTrue(all(proplist))
            for proplist in may_props:
                #assuming at least one of the articles has the property. if not, break
                self.assertTrue(any(proplist))

            
