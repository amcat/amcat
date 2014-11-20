# ##########################################################################
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
from amcat.models import ArticleSet
from amcat.scripts.article_upload.upload import UploadScript
from amcat.tools.toolkit import readDate
from amcat.models.medium import Medium
from amcat.models.article import Article
from lxml import html
from html2text import html2text
import re
import logging;

log = logging.getLogger(__name__)
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES as MEDIUM_ALIASES


class BZK(UploadScript):
    def _scrape_unit(self, _file):
        if type(_file) == unicode:  #command line
            etree = html.fromstring(_file)
        else:  #web interface
            try:
                etree = html.parse(_file).getroot()
            except IOError as e:
                log.exception("Failed html.parse")
                raise TypeError(
                    "failed HTML parsing. Are you sure you've inserted the right file?\n{e}".format(**locals()))

        title = etree.cssselect("title")
        if title:
            title_text = title[0].text.lower().strip()
            if "intranet/rss" in title_text or "werkmap" in title_text:
                for article in self.scrape_1(etree, title_text):
                    yield article
        elif etree.cssselect("h1"):
            for article in self.scrape_2(etree):
                yield article
        else:
            for article in self.scrape_3(etree):
                yield article

    def scrape_1(self, _html, t):
        """format of mostly 2013"""
        if "werkmap" in t:
            divs = _html.cssselect("#articleTable div")
        elif "intranet/rss" in t:
            divs = [div for div in _html.cssselect("#sort div") if "sort_" in div.get('id')]
        else:
            raise ValueError("Neither 'werkmap' nor 'intranet/rss' in html.")

        for div in divs:
            article = Article(metastring={'html': div})
            article.headline = div.cssselect("#articleTitle")[0].text_content()
            article.text = div.cssselect("#articleIntro")[0]
            articlepage = div.cssselect("#articlePage")

            if articlepage:
                article.pagenr, article.section = self.get_pagenum(articlepage[0].text)

            article.medium = self.get_medium(div.cssselect("#sourceTitle")[0].text)
            date_str = div.cssselect("#articleDate")[0].text

            try:
                article.date = readDate(date_str)
            except ValueError:
                log.error("parsing date \"{date_str}\" failed".format(**locals()))
            else:
                yield article

    def scrape_2(self, _html):
        """New format as of 2014 and a few days before"""
        title = _html.cssselect("h1")[0]
        if not title.text:
            title = title.cssselect("span")[0]
        docdate = readDate(title.text.split("-")[1])

        # split body by <hr>
        items = []
        item = []
        

        if len(_html.cssselect("body > hr")) == 0:
            #if len(_html.cssselect("body > div > hr")) == 0:
                # extra extra div  and span wrapper as of 2014-11-20
            #    tags = _html.cssselect("body > div > div > span > *")
            #else: # extra div wrapper as of 2014-04-08
                tags = _html.cssselect("body > div > *")
        else:
            tags = _html.cssselect("body > *")

        for child in tags:
            if child.tag == "hr" or (child.tag == "div" and child.cssselect("span > hr")):
                items.append(item)
                item = []
            else:
                item.append(child)

        #first item is the index
        items = items[1:]
        for item in items:
            article = self.parse_item(item)
            if not article.date:
                article.date = docdate
            yield article

    def scrape_3(self, _html):
        """Some ugly MS Word format, as of 2014-03-03"""
        # Partition articles
        part = []
        articles = []
        for tag in _html.cssselect("body > div > *"):
            if tag.cssselect("hr"):
                articles.append(part)
                part = []
            else:
                part.append(tag)
        for tags in articles[1:]:
            article = Article()
            dateline = tags[1].text_content().strip()
            article = self.parse_dateline(dateline, article)
            article.headline = tags[1].text_content().strip()
            html_str = "".join([html.tostring(t) for t in tags[2:]])
            article.text = html2text(html_str)
            article.metastring = {'html': html_str}

            yield article


    def parse_dateline(self, text, article):
        bits = text.split()
        if "-" in bits[-1]:
            article.date = readDate(bits[-1])
            article.medium = self.get_medium(" ".join(bits[:-1]))
        elif bits[-1].isdigit() and bits[-3].isdigit():
            article.date = readDate(" ".join(bits[-3:]))
            article.medium = self.get_medium(" ".join(bits[:-3]))
        else:
            article.medium = self.get_medium(" ".join(bits))
            article.date = None
        return article

    def _parse_text(self, item):
        paragraphs = (tag for tag in item if tag.tag in ("p", "div"))
        return "\n".join(html2text(html.tostring(p)) for p in paragraphs)

    def parse_item(self, item):
        #item: a list of html tags
        article = Article(metastring={})
        article.text = self._parse_text(item)
        for tag in item:
            if tag.tag == "h2":
                if tag.text:
                    article.headline = tag.text
                else:
                    article.headline = tag.cssselect("span")[0].text_content()
            elif tag.tag == "i" or (tag.tag == "p" and tag.cssselect("i")):
                article = self.parse_dateline(tag.text_content(), article)
        if not article.headline:
            raise Exception("Article has no headline")
        return article

    def get_medium(self, text):
        if not text:
            text = "unknown"
        if text in MEDIUM_ALIASES.keys():
            return Medium.get_or_create(MEDIUM_ALIASES[text])
        else:
            return Medium.get_or_create(text)

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


class TestBZK(amcattest.AmCATTestCase):
    def setUp(self):
        from django.core.files import File
        import os.path

        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'bzk')
        self.bzk = BZK(project=amcattest.create_test_project().id,
                       file=File(open(os.path.join(self.dir, 'test.html'))),
                       articlesets=[amcattest.create_test_set().id])
        self.result = ArticleSet.objects.get(id=self.bzk.run()[0]).articles.all()

    def test_scrape_unit(self):
        self.assertTrue(self.result)

    def test_scrape_file(self):
        must_props = ('headline', 'text', 'medium', 'date')
        must_props = [[getattr(a, prop) for a in self.result] for prop in must_props]

        for proplist in must_props:
            self.assertTrue(all(proplist))
