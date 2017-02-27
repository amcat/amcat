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
import io
import re

from lxml import etree

from amcat.scripts.article_upload.upload import UploadScript
from amcat.scripts.article_upload.upload_plugin import UploadPlugin
from amcat.models.article import Article
from amcat.tools import toolkit

@UploadPlugin(name="DeFacto Student")
class DeFactoStudent(UploadScript):
    def split_file(self, f):
        html = get_html(to_buffer(f))
        return split_html(html)

    def _scrape_unit(self, element):
        yield get_article(element)


def to_buffer(file):
    if hasattr(file, "read"):
        return file.read()
    return file


def get_article(e):
    title = get_title(e)
    body = get_body(e)
    medium, date, page = get_meta(e)
    section = get_section(e)

    article = Article(title=title, text=body, date=date)

    if page is not None:
        article.set_property("page_num", page)

    if section is not None:
        article.set_property("section", section)

    if medium is not None:
        article.set_property("medium", medium)

    return article


def parse_ressort(text):
    m = re.search("Ressort:(.*)", text)
    if m:
        return m.group(1).strip()
    else:
        raise ValueError("Cannot parse ressort string {text!r}".format(**locals()))


def parse_meta(text):
    m = re.match(r"(.*?)\s*(Nr. \d+)? vom (\d\d\.\d\d\.\d\d\d\d)( \d\d[.:]\d\d\b)?(.*)", text)
    if not m:
        raise ValueError("Cannot parse meta string {text!r}".format(**locals()))
    medium, nr, date, time, pagestr = m.groups()
    if medium.startswith('"') and medium.endswith('"'):
        medium = medium[1:-1]

    if time:
        date = date + time.replace(".", ":")
    date = toolkit.read_date(date)
    m = re.search("Seite:? (\d+)", pagestr)
    if m:
        page = int(m.group(1))
    else:
        page = None

    return medium, date, page


def get_html(html_bytes):
    parser = etree.HTMLParser()
    return etree.parse(io.BytesIO(html_bytes), parser)


def split_html(html):
    return html.xpath("//div[@class='eintrag']")


def get_meta(div):
    return parse_meta(div.find("pre").text)


def get_title(div):
    return div.find("h3").text.strip()


def get_section(div):
    try:
        return parse_ressort(div.find("pre").text)
    except ValueError:
        return  # no ressort?


def get_body(div):
    return "\n\n".join(stringify_children(p).strip() for p in div.findall("p")).strip()


def stringify_children(node):
    """http://stackoverflow.com/questions/4624062/get-all-text-inside-a-tag-in-lxml"""
    from lxml.etree import tostring
    from itertools import chain
    parts = ([node.text] +
             list(chain(*([c.text, tostring(c, encoding="utf-8").decode('utf-8'), c.tail] for c in
                          node.getchildren()))) +
             [node.tail])
    # filter removes possible Nones in texts and tails
    return ''.join(filter(None, parts))


if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli

    run_cli(handle_output=False)
