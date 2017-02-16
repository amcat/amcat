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
This scraper parses APA articles. The general flow of the scraper is (when
given an RTF file):

    1. fix_rtf(): the downloaded documents are malformed as they contain characters
                  not specified in the RTF format. Furthermore, some documents seem
                  to contain errors concerning incorrectly formatted codepoints.

    2. to_xml(): converts the fixed RTF document to XML using rtf2xml (commandline
                 utility which needs to be installed separately).

    3. parse_xml(): parse xml using lxml
    4. get_pages(): split articles

    5. parse_page(): returns (dict, string) with metadata and the text of the given
                     article. It can raise a ValueError if it thinks the article is
                     malformed.

    6. to_article(): given the metadata and text it will return a Article object.

"""
from tempfile import NamedTemporaryFile
from lxml.html import fromstring

import re
import sys
import itertools
import lxml.html
import logging

from amcat.models import Article
from amcat.scripts.article_upload.upload import UploadScript, Plugin
from amcat.tools.toolkit import read_date

log = logging.getLogger(__name__)

FS20 = "\\fs20"
PAGE_BREAK = "page-break"
STOP_AT = re.compile(
    r"((Gespeicherter Anhang:)|(Der gegenst\xc3\xa4ndliche Text ist eine Abschrift)|(Gespeicherte Anh\xc3\xa4nge))")

# 11.05.2004
_RE_DATE = "(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})"
RE_DATE = re.compile(_RE_DATE)

# 15.Aug 2013
_RE_DATE2 = "(?P<day>\d{2})\.(?P<month>\w{3}) (?P<year>\d{4})"
RE_DATE2 = re.compile(_RE_DATE2)

# 11.05.2004 18.00 Uhr
_RE_DATETIME = "(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4}) (?P<hour>\d{2})\.(?P<minute>\d{2}) Uhr"
RE_DATETIME = re.compile(_RE_DATETIME)

# Title
RE_MEDIUM = re.compile("(?P<medium>.*) vom ({_RE_DATE})".format(**locals()))
RE_MEDIUM_QUOTE = re.compile("\"(?P<medium>.+)\" (?P<section>.+) vom ({_RE_DATE})".format(**locals()))

# Seite: 14
RE_PAGENR = re.compile("Seite:? *L?(?P<pagenr>\d+)")

# Ressort: Chronik
RE_SECTION = re.compile("Ressort: *(?P<section>[^;:.?!-]+)")

# Von Robert Zwickelsdorfer
# (Sentence must start with Von)
RE_AUTHOR = re.compile("^Von (?P<author>[^0-9]+)$")

# All regular expressions which can match metadata
META_RE = (RE_DATE, RE_DATE2, RE_DATETIME, RE_PAGENR, RE_SECTION, RE_AUTHOR, RE_MEDIUM, RE_MEDIUM_QUOTE)

UNDECODED = b"NON_DECODED_CHARACTER"
UNDECODED_UNICODE = b"NON_DECODED_UNICODE_CHARACTER"

RE_UNICHAR = re.compile(r"(?P<match>\\u(?P<hex>[0-9]+)\?)", re.UNICODE)

### FIXING AND PARSING ###
def _fix_fs20(s):
    last = 0
    while True:
        pos = s.find(FS20, last + len(FS20))
        if pos == -1:
            break
        yield s[last:pos + len(FS20)]
        last = pos + len(FS20)
    yield s[last:]


def fix_fs20(s):
    return bytes(" ").join(_fix_fs20(s))


def fix_rtf(s):
    """
    This function does two things:
      1. Fixing broken 'tags'
      2. Replacing non-ASCII characters with UNDECODED
      3. Replacing new page-indicators ("____") with rtf page tag
    
    @param s: bytes containing rtf
    @return: rtf bytes
    """
    s = fix_fs20(s.replace('_' * 67, '\\page'))

    for match, correct in get_unencoded_unicode(s):
        s = s.replace(match, UNDECODED_UNICODE, 1)

    return "".join(UNDECODED if ord(b) >= 128 else b for b in s)


def get_unencoded(s):
    """Get characters with a value higher than 128 (non-ASCII characters)"""
    return (bytes(b) for b in s if ord(b) >= 128)


def get_unencoded_unicode(s):
    for groups in (m.groupdict() for m in RE_UNICHAR.finditer(s)):
        yield bytes(groups['match']), chr(int(groups['hex']))


def to_html(original_rtf, fixed_rtf):
    html = None
    from sh import unrtf

    with NamedTemporaryFile() as xml:
        xml.write(fixed_rtf)
        xml.flush()
        html = bytes(unrtf(xml.name))

    for u in get_unencoded(original_rtf):
        html = html.replace(UNDECODED, u, 1)

    html = html.decode("latin-1")

    for match, correct in get_unencoded_unicode(original_rtf):
        html = html.replace(UNDECODED_UNICODE, correct, 1)

    return html.replace("&gt;", ">").replace("&lt;", "<")


def parse_html(html):
    # See issue #574. Splitting the RTF in multiple documents considered too
    # much work compared with this hack. 
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(3000)

    try:
        return fromstring(html)
    finally:
        sys.setrecursionlimit(limit)


def _get_pages(elements):
    return list(itertools.takewhile(lambda el: el.tag != "hr", elements))


def get_pages(doc):
    elements = doc.iterdescendants()
    pages = len(doc.cssselect("hr")) + 1
    return (_get_pages(elements) for i in range(pages))


def get_descendants(elements):
    """Given a list of elements yield all descendants and the element itself"""
    for element in elements:
        yield element
        for e in element.iterdescendants():
            yield e


def remove_tree(elements, tags):
    """
    Given a list of elements, remove all elements and their descendants
    which tag is `tag`.
    """
    tag_elements = (e for e in elements if e.tag in tags)
    elements -= set(get_descendants(tag_elements))


def get_nonempty(elements):
    return {e for e in elements if e.text is not None}


def get_roots(elements):
    non_roots = set()
    for el in elements:
        non_roots |= set(get_descendants(el))
    return set(elements) - non_roots


def do_stop(e):
    return not STOP_AT.search(e.text or "")


def get_text(elements):
    """"""
    for element in itertools.takewhile(do_stop, elements):
        if element.tag == "br":
            yield "\n"
        elif element.text is not None:
            yield element.text


def _get_metadata(metadata, element):
    for expr in META_RE:
        match = expr.search(element.text)
        if match:
            metadata.update(match.groupdict())
            yield expr


def get_metadata(metadata, element):
    """
    Matches metadata expressions against the text attribute of `element`
    and updates `metadata` accordingly.
    
    @return: True if metadata found, False if not"""
    if not element.text: return False

    it = _get_metadata(metadata, element)
    try:
        next(it)
    except StopIteration:
        return False
    list(it)
    return True


def parse_page(doc_elements):
    """Parses an APA page given in a list of Etree elements."""
    doc, elements = doc_elements
    elements = [e for e in elements if not isinstance(e, lxml.html.HtmlComment)]

    headline = set(get_descendants(doc.cssselect("b"))) & set(elements)
    meta = (set(get_descendants(doc.cssselect("i"))) & set(elements)) - headline
    text = set(elements) - (headline | meta)
    headline = sorted(get_roots(headline), key=lambda e: elements.index(e))

    if not headline:
        raise ValueError("No possible headlines found.")

    remove_tree(meta, ["b"])
    remove_tree(text, ["b", "i"])

    # Some text in italics is no metadata. We only use text before headline elements
    # for metadata.
    lesser_than_headline = lambda e: elements.index(e) <= elements.index(headline[0])
    meta = get_nonempty(filter(lesser_than_headline, meta))

    # Parse metadata
    metadata = {}
    for el in list(meta):
        if get_metadata(metadata, el):
            meta.remove(el)

    if meta:
        metadata["byline"] = " - ".join(m.text for m in meta)

    # Convert date properties to datetime object
    year, month, day = metadata["year"], metadata["month"], metadata["day"]
    hour, minute = metadata.get("hour"), metadata.get("minute")

    datestring = "{day} {month} {year}"
    if hour is not None and minute is not None:
        datestring += ", {hour}:{minute}"

    metadata["date"] = read_date(datestring.format(**locals()))
    for prop in ("year", "month", "day", "hour", "minute"):
        if prop in metadata:
            del metadata[prop]

    # Clean data and get headline
    metadata["medium"] = metadata.get("medium", "APA - Unknown").strip().strip('"')
    medium, headline = metadata["medium"], "".join(["".join(e.itertext()) for e in headline])

    if medium in headline:
        headline = headline.split("-", medium.count("-") + 1)[-1]

    metadata["headline"] = headline

    # Get text. Since ordering is lost in sets, restore original order of elements
    return metadata, "".join(get_text(sorted(text, key=lambda e: elements.index(e)))).strip()


### NAVIGATOR INTEGRATION ###
class APAForm(UploadScript.form_class):
    pass

@Plugin(label="APA")
class APA(UploadScript):
    options_form = APAForm

    def parse_document(self, paragraphs):
        metadata, text = parse_page(paragraphs)
        metadata["medium"] = Medium.get_or_create(metadata["medium"])

        return Article(text=text, **metadata)

    def split_file(self, file):
        original_rtf, fixed_rtf = file.bytes, fix_rtf(file.bytes)
        doc = parse_html(to_html(original_rtf, fixed_rtf))

        for i, page in enumerate(get_pages(doc)):
            yield doc, page


"""if __name__ == '__main__':
    original_rtf = open(sys.argv[1], 'rb').read()
    fixed_rtf = fix_rtf(original_rtf)
    html = to_html(original_rtf, fixed_rtf)
    #html = open("blaat.html").read()
    doc = parse_html(html)
    pages = list(get_pages(doc))

    for page in pages:
        metadata, text = parse_page((doc, page))
        print(text)
        print("-----")"""

if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli

    run_cli(handle_output=False)
