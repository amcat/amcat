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
from typing import Iterable

from django.core.files.uploadedfile import UploadedFile
from lxml.html import fromstring, etree

import re
import sys
import itertools
import lxml.html
import logging

import settings
from amcat import models
from amcat.models import Article
from amcat.scripts.article_upload.upload import UploadScript, ArticleField, ParseError
from amcat.scripts.article_upload.upload_plugins import UploadPlugin
from amcat.tools.toolkit import read_date

log = logging.getLogger(__name__)

FS20 = "\\fs20"
PAGE_BREAK = "page-break"
STOP_AT = re.compile(
    r"((Gespeicherter Anhang:)|(Der gegenst\xc3\xa4ndliche Text ist eine Abschrift)|(Gespeicherte Anh\xc3\xa4nge))")

# apparently new page separators can contain RTF tags
RES_NEWPAGE = (re.compile(r"_(_|(\\[A-Za-z0-9]+\s?))+_"), re.compile(r"\\sect"))

# 11.05.2004
_RE_DATE = "(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})"
RE_DATE = re.compile(_RE_DATE)

# 15.Aug 2013
_RE_DATE2 = "(?P<day>\d{2})\.(?P<month>\w{3}) (?P<year>\d{4})"
RE_DATE2 = re.compile(_RE_DATE2)

# 11.05.2004 18.00 Uhr
_RE_DATETIME = "(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4}) (?P<hour>\d{2})[.:](?P<minute>\d{2}) Uhr"
RE_DATETIME = re.compile(_RE_DATETIME)

# Title
RE_MEDIUM = re.compile("(?P<medium>.*) vom ({_RE_DATE})".format(**locals()))
RE_MEDIUM_QUOTE = re.compile("\"(?P<medium>.+)\" (?P<section>.+) vom ({_RE_DATE})".format(**locals()))
RE_MEDIUM_ONLINE = re.compile("\"(?P<medium>.+)\" ((?P<section>.+) )?gefunden am ({_RE_DATE})".format(**locals()))

# Seite: 14
RE_PAGENR = re.compile("Seite:? *L?(?P<pagenr>\d+)")

# Ressort: Chronik
RE_SECTION = re.compile("Ressort: *(?P<section>[^;:.?!-]+)")

# Von Robert Zwickelsdorfer
# (Sentence must start with Von)
RE_AUTHOR = re.compile("^Von (?P<author>[^0-9]+)$")

# All regular expressions which can match metadata
META_RE = (
RE_DATE, RE_DATE2, RE_DATETIME, RE_PAGENR, RE_SECTION, RE_AUTHOR, RE_MEDIUM, RE_MEDIUM_QUOTE, RE_MEDIUM_ONLINE)

UNDECODED = "NON_DECODED_CHARACTER"
UNDECODED_UNICODE = "NON_DECODED_UNICODE_CHARACTER"

RE_UNICHAR = re.compile(r"(?P<match>\\u(?P<ord>[0-9]+)\?)", re.UNICODE)

# any non-word sequence.
RE_NONWORD = re.compile(r"[^\w]+")

RE_WS = re.compile(r"\s+")

DEFAULT_FORMAT = "{}_NOT_GIVEN"

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
    return " ".join(_fix_fs20(s))

def as_escape(ch):
    return "\\\\u{:04}?".format(ord(ch))

def fix_rtf(s):
    """
    This function does four things:
      1. Fixing broken 'tags'
      2. Replacing non-ASCII characters with UNDECODED
      3. Double-escape unicode escape sequences, \u0000? -> \\u0000? .
      4. Replacing new page-indicators ("____" or otherwise "\sect") with rtf page tag
    
    @param s: bytes containing rtf
    @return: rtf bytes
    """
    for re in RES_NEWPAGE:
        if re.search(s) is None:
            continue
        s = re.sub("\\page", s)

    s = fix_fs20(s)

    s = RE_UNICHAR.sub(lambda m: "\\" + m.group(), s)
    s = "".join(as_escape(ch) if ord(ch) >= 128 else ch for ch in s)
    return s


def get_unencoded(s):
    """Get characters with a value higher than 128 (non-ASCII characters)"""
    return [b for b in s if ord(b) >= 128]


class TooManyAttributesError(BaseException):
    pass


class ApaError(ValueError):
    pass


class EmptyPageError(ApaError):
    pass


def unrtf(name):
    from subprocess import Popen, PIPE
    try:
        p = Popen(["unrtf", name], stdout=PIPE, stderr=PIPE)
    except FileNotFoundError:
        raise RuntimeError("unrtf executable not found.")
    stdout, stderr = p.communicate()
    if settings.DEBUG:
        open("/tmp/apa_unrtf.html", "wb").write(stdout)
    if len(stderr) > 100:
        if stderr.count(b"Too many attributes") > 10:
            raise TooManyAttributesError()
    if p.returncode > 0:
        raise ParseError("Failed to parse RTF: {}".format(stderr))
    return stdout.decode()


def compartmentalize(rtf):
    """
    Split the rtf into small paragraph sized groups to prevent formatting directives from leaking out of their scope,
    which would throw off unrtf.
    """
    boundary = "\n\\par\n"
    parts = rtf.split(boundary)
    if len(parts) < 3:  # at least 1 head, 1+ middle, 1 tail parts are needed
        return rtf

    middle = "\n}}{}{{\n".format(boundary).join(parts[1:-1])

    return "{head}{boundary}{{{body}}}{boundary}{tail}".format(head=parts[0], boundary=boundary, body=middle,
                                                               tail=parts[-1])


def to_html(original_rtf, fixed_rtf, fallback=False):
    html = None

    if not fallback:
        fixed_rtf2 = compartmentalize(fixed_rtf)
    else:
        fixed_rtf2 = fixed_rtf

    with NamedTemporaryFile() as rtf:
        rtf.write(fixed_rtf2.encode("ascii"))
        rtf.flush()
        html = str(unrtf(rtf.name))

    for u in get_unencoded(original_rtf):
        html = html.replace(UNDECODED, u, 1)

    html = RE_WS.sub(" ", html)

    # Convert previously escaped RTF unicode escape sequences to HTML, \u0000? -> &#0000;
    html = RE_UNICHAR.sub(lambda m: "&#{};".format(m.group("ord")), html)
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


def split_on_tag(tag, elements):
    line = []
    for element in elements:
        if element.tag == tag:
            yield line
            line = []
        else:
            line.append(element)
    if line:
        yield line


def try_alternative(elements):
    lines = split_on_tag("br", elements)
    metadata = {}
    success = False
    for line in lines:
        field = None
        descs = []
        for el in line:
            if el.tag == "b":
                descs = list(get_descendants(el))
                field = "".join(get_text(descs)).split(":")[0].lower()
                break
        value = "".join(get_text([el for el in line if el not in descs])).strip()
        if field == "inhalt":
            success = True
            break
        if field and value:
            metadata[field] = value
    text = "".join(get_text(elements))
    print(metadata, text)
    if success:
        return metadata, text
    return None


def parse_page(doc_elements):
    """Parses an APA page given in a list of Etree elements."""
    doc, elements = doc_elements
    elements = [e for e in elements if not isinstance(e, lxml.html.HtmlComment)]

    result = try_alternative(elements)
    if result is not None:
        return result

    headline = set(get_descendants(doc.cssselect("b"))) & set(elements)
    meta = (set(get_descendants(doc.cssselect("i"))) & set(elements)) - headline
    text = set(elements) - (headline | meta)
    headline = sorted(get_roots(headline), key=lambda e: elements.index(e))

    if not headline:
        raise ApaError("No possible headlines found.")

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

    datestring = "{day}.{month}.{year}"
    if hour is not None and minute is not None:
        datestring += ", {hour}:{minute}"

    metadata["date"] = read_date(datestring.format(**locals()))
    for prop in ("year", "month", "day", "hour", "minute"):
        if prop in metadata:
            del metadata[prop]

    # Clean data and get headline
    metadata["medium"] = metadata.get("medium", "APA - Unknown").strip().strip('"')
    medium, headline = metadata["medium"].strip(), "".join(["".join(e.itertext()) for e in headline]).strip()

    if medium in headline:
        headline = headline.split("-", medium.count("-") + 1)[-1]

    metadata["title"] = headline

    if "section" in metadata and metadata["section"] is None:
        del metadata["section"]

    # Get text. Since ordering is lost in sets, restore original order of elements
    text = "".join(get_text(sorted(text, key=lambda e: elements.index(e)))).strip()

    metadata["length"] = sum(1 for w in RE_NONWORD.split(text) if w)

    return metadata, text


### NAVIGATOR INTEGRATION ###

class APAForm(UploadScript.form_class):
    pass


@UploadPlugin(label="APA", mime_types=("text/rtf",))
class APA(UploadScript):
    options_form = APAForm

    @classmethod
    def get_fields(cls, upload: models.UploadedFile):
        upload.encoding_override('binary')
        f = next(upload.get_files())
        if b'Inhalt' not in f.read(4000):
            return [
                ArticleField("title", "title"),
                ArticleField("byline", "byline"),
                ArticleField("text", "text"),
                ArticleField("date", "date"),
                ArticleField("medium", "medium"),
                ArticleField("pagenr", "pagenr"),
                ArticleField("section", "section"),
                ArticleField("author", "author"),
                ArticleField("length", "length_int")
            ]
        else:
            return [
                ArticleField("titel", "title"),
                ArticleField("datum", "date"),
                ArticleField("text", "text"),
                ArticleField("publikation"),
                ArticleField("datenbank", "database"),

            ]

    def parse_file(self, file: UploadedFile, _) -> Iterable[Article]:
        data = file.read()
        try:
            for para in self.split_file(data):
                yield self.parse_document(para)
        except ApaError:
            log.error("APA parse attempt failed.")
            if settings.DEBUG:
                log.error("The generated HTML can be found in /tmp/apa_unrtf.html")
            raise

    def parse_document(self, paragraphs) -> Article:
        metadata, text = parse_page(paragraphs)
        return Article(**self.map_article(dict(metadata, text=text), default={"text": "NO_TEXT", "title": "NO_TITLE"}))

    @classmethod
    def split_file(cls, data, fallback=False):
        original_rtf, fixed_rtf = data, fix_rtf(data)
        html = to_html(original_rtf, fixed_rtf, fallback=fallback)
        open("/tmp/unrtf.html", "w").write(html)
        doc = parse_html(html)

        for i, page in enumerate(get_pages(doc)):
            yield doc, page


if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli

    run_cli(handle_output=False)
