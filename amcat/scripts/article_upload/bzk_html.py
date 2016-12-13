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

import logging
import re
from collections import defaultdict

from lxml import html

from amcat.models.article import Article
from amcat.scripts.article_upload.upload import UploadScript, ParseError, ArticleField
from amcat.tools.toolkit import read_date

log = logging.getLogger(__name__)
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES as MEDIUM_ALIASES


class BZK(UploadScript):

    @classmethod
    def get_fields(cls, file, encoding):
        text = cls.textio(file, encoding)
        values = defaultdict(list)
        for i, art_dict in zip(range(5), cls._scrape_unit(text.read())):
            for k, v in art_dict.items():
                values[k].append(v)
        for k, v in values.items():
            yield ArticleField(k, k, v)
        
    def parse_file(self, file):
        text = self.textio(file, self.options['encoding'])
        for art_dict in self._scrape_unit(text.read()):
            yield Article.fromdict(self.map_article(art_dict))

    @classmethod
    def _scrape_unit(cls, _file):
        if isinstance(_file, str):
            # command line
            etree = html.fromstring(_file)
        else:
            # web interface
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
                for article in cls.scrape_1(etree, title_text):
                    yield article
        elif etree.cssselect("h1"):
            for article in cls.scrape_2(etree):
                yield article
        else:
            for article in cls.scrape_3(etree):
                yield article

    @classmethod
    def scrape_1(cls, _html, t):
        """format of mostly 2013"""
        if "werkmap" in t:
            divs = _html.cssselect("#articleTable div")
        elif "intranet/rss" in t:
            divs = [div for div in _html.cssselect("#sort div") if "sort_" in div.get('id')]
        else:
            raise ValueError("Neither 'werkmap' nor 'intranet/rss' in html.")

        for div in divs:
            article = {"html": div.text_content()}
            article["title"] = div.cssselect("#articleTitle")[0].text_content()
            article["text"] = div.cssselect("#articleIntro")[0].text_content()
            articlepage = div.cssselect("#articlePage")

            if articlepage:
                article["pagenr"], article["section"] = cls.get_pagenum(articlepage[0].text_content())

            article["medium"] = cls.get_medium(div.cssselect("#sourceTitle")[0].text_content())
            date_str = div.cssselect("#articleDate")[0].text_content()

            try:
                article["date"] = read_date(date_str)
            except ValueError:
                log.error("parsing date \"{date_str}\" failed".format(**locals()))
            else:
                yield article

    @classmethod
    def scrape_2(cls, _html):
        """New format as of 2014 and a few days before"""
        title = _html.cssselect("h1")[0]
        if not title.text:
            title = title.cssselect("span")[0]
        docdate = read_date(title.text.split("-")[1])

        # split body by <hr>
        items = []
        item = []
        
        if len(_html.cssselect("body > hr")) == 0:
            # select MS Word div wrapper
            tags = _html.cssselect("body > div.WordSection1 > *")
            if len(tags) == 0:
                    raise ParseError("Document format is not supported")

        else:
            tags = _html.cssselect("body > *")

        for child in tags:
            if child.tag == "hr" or (child.tag == "div" and child.cssselect("span > hr")):
                items.append(item)
                item = []
            else:
                item.append(child)

        # first item is the index
        items = items[1:]
        for item in items:
            article = cls.parse_item(item)
            if not article["date"]:
                article["date"] = docdate
            yield article

    @classmethod
    def scrape_3(cls, _html):
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
            article = {}
            dateline = tags[1].text_content().strip()
            article = cls.parse_dateline(dateline, article)
            article["title"] = tags[1].text_content().strip()
            html_str = "\n".join([html.tostring(t, method="text", encoding='utf8') for t in tags[2:]])
            article["text"] = html_str
            article["html"] = html_str

            yield article

    @classmethod
    def parse_dateline(cls, text, article):
        bits = text.split()
        if "-" in bits[-1]:
            article["date"] = read_date(bits[-1])
            article["medium"] = cls.get_medium(" ".join(bits[:-1]))
        elif bits[-1].isdigit() and bits[-3].isdigit():
            article["date"] = read_date(" ".join(bits[-3:]))
            article["medium"] = cls.get_medium(" ".join(bits[:-3]))
        else:
            article["medium"] = cls.get_medium(" ".join(bits))
            article["date"] = None
        return article

    @staticmethod
    def _parse_text(item):
        paragraphs = (tag for tag in item if tag.tag in ("p", "div"))
        return "\n".join((html.tostring(p, method="text", encoding="utf8").decode()) for p in paragraphs)

    @classmethod
    def parse_item(cls, item):
        #item: a list of html tags
        article = {}
        article["text"] = cls._parse_text(item)
        headline_found = False
        dateline_found = False
        for tag in item:
            if tag.tag == "h2" and not headline_found:
                if tag.text:
                    article["title"] = tag.text
                else:
                    article["title"] = tag.cssselect("span")[0].text_content()
                headline_found = True
            elif tag.tag == "i" or (tag.tag == "p" and tag.cssselect("i")) and not dateline_found:
                article = cls.parse_dateline(tag.text_content(), article)
                dateline_found = True
        if not article.get("title"):
            raise Exception("Article has no headline")
        return article

    @staticmethod
    def get_medium(text):
        if not text:
            text = "unknown"
        if text in MEDIUM_ALIASES.keys():
            return MEDIUM_ALIASES[text]
        else:
            return text

    @staticmethod
    def get_pagenum(text):
        p = re.compile("pagina ([0-9]+)([,\-][0-9]+)?([a-zA-Z0-9 ]+)?")
        m = p.search(text.strip())
        pagenum, otherpage, section = m.groups()
        if section:
            section = section.strip()
        return int(pagenum), section


if __name__ == "__main__":
    from amcat.scripts.tools import cli

    cli.run_cli(BZK)

