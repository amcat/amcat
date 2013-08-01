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
from tempfile import NamedTemporaryFile, mkstemp
from collections import defaultdict

import re
import subprocess
import rtfunicode
import sys
import StringIO
import datetime

from sh import rtf2xml
from lxml import etree

import StringIO

FS20 = "\\fs20"
PAGE_BREAK = "page-break"
STOP_AT = ["Gespeicherter Anhang:"]

# 11.05.2004
RE_DATE = re.compile("(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4})")

# 11.05.2004 18.00 Uhr
RE_DATETIME = re.compile("(?P<day>\d{2})\.(?P<month>\d{2})\.(?P<year>\d{4}) (?P<hour>\d{2})\.(?P<minute>\d{2}) Uhr")

# Seite: 14
RE_PAGE = re.compile("Seite: *(?P<page>\d*)")

# Ressort: Chronik
RE_SECTION = re.compile("Ressort: *(?P<section>[^;:.?!-]*)")

# Von Robert Zwickelsdorfer
# (Sentence must start with Von)
RE_AUTHOR = re.compile("^Von (?P<author>[^0-9]*)$")

def _fix_fs20(s):
    last = 0
    while True:
        pos = s.find(FS20, last+len(FS20))
        if pos == -1: break
        yield s[last:pos+len(FS20)]
        last = pos + len(FS20)
    yield s[last:]

def fix_fs20(s):
    return bytes(" ").join(_fix_fs20(s))

def fix_rtf(s):
    s = fix_fs20(s.replace('_'*67, '\\page'))
    res = StringIO.StringIO()
    
    for b in s:
        if ord(b) >= 128:
            # strip off substition char - by now writing the escape directly is probably
            # easier than unsing rtfunicode...
            b = b.decode('latin-1').encode('rtfunicode')[:-1] 
        res.write(b)

    return res.getvalue()

def to_xml(rtf):
    with NamedTemporaryFile() as xml:
        xml.write(rtf)
        xml.flush()
        return (bytes(rtf2xml(xml.name))
                    .replace(' xmlns="http://rtf2xml.sourceforge.net/"', '')
                    .replace(' encoding="us-ascii"?>', '?>')
        )

def get_pages(doc):
    page = []

    for action, elem in doc:
        if elem.tag == "para":
            if not "".join(elem.itertext()).strip():
                # Skip empty paragraphs
                continue
            page.append(elem)
        elif elem.tag == PAGE_BREAK:
            yield page
            page = []

def get_datetime(match):
    match = match.groupdict()
    for key in ("year", "month", "day", "hour", "minute"):
        match[key] = int(match.get(key, 0))
    return datetime.datetime(**match)

def search(text, metadata, label, re, _type=unicode):
    match = re.search(text)
    if match and not label in metadata:
        metadata[label] = _type(match.groupdict()[label])
        return True

def search_all(text, metadata):
    return (search(text, metadata, "page", RE_PAGE, int) or
                search(text, metadata, "section", RE_SECTION) or
                search(text, metadata, "author", RE_AUTHOR))
    
def parse_text(paragraphs):
    text = ""
    while paragraphs and text not in STOP_AT:
        if text: yield text.strip()
        text = "".join(paragraphs.pop(0).itertext()).strip()

def parse_page(paragraphs):
    """Parses an APA page given in a list of Etree elements."""
    metadata = dict()

    # Parse metadata
    while paragraphs:
        paragraph = paragraphs.pop(0)
        text = "".join(paragraph.itertext()).strip()

        if "medium" not in metadata and "vom" in text:
            # ProSieben AustriaNews 18:00 vom 11.05.2013 18.00 Uhr
            metadata["medium"] = text.rsplit("vom", 1)[0].strip().strip('"')
            changed = True

            # Search date(time) from least to most specific
            for date_regex in (RE_DATE, RE_DATETIME):
                match = date_regex.search(text)
                if match: metadata["date"] = get_datetime(match)

            search_all(text, metadata)
            continue

        # Check for page number, section, author. When at least one of those is
        # found and not /already/ found, contintue while this can't be
        # the headline
        if search_all(text, metadata):
            continue

        if len(text.split()) <= 3:
            # Ignoring setence with less than 3 words. Probably the version.
            metadata["version"] = text
            continue

        # Check for headline, which can include other information than the
        # headline itself like the date and medium
        if "medium" in metadata and "date" in metadata:
            headline = text
            if metadata["medium"] in headline:
                split_at = 1 + metadata["medium"].count("-")
                headline = headline.split("-", split_at)[-1]
            metadata["headline"] = headline.strip()

            # Headline found, parse text now!
            break
            
    if not paragraphs:
        raise ValueError("Could not found medium and date in this article.")

    # Treat the remaining paragraphs as text
    return metadata, "\n\n".join(parse_text(paragraphs))

def to_article(metadata, text):
    pass

def parse_xml(xml):
    return etree.iterparse(StringIO.StringIO(xml))

if __name__ == '__main__':
    rtf = fix_rtf(open(sys.argv[1], 'rb').read())
    doc = parse_xml(to_xml(rtf))

    for page in get_pages(doc):
        print(parse_page(page))

