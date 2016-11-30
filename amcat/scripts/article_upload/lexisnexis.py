#!/usr/bin/python
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
This module contains a (semi-machine readable) lexisnexis parser.
"""

import re
import collections
import logging

from amcat.scripts.article_upload.upload import UploadScript, ParseError
from amcat.scripts.article_upload import fileupload
from amcat.tools import toolkit
from amcat.models.article import Article

from io import StringIO


log = logging.getLogger(__name__)

# Regular expressions used for parsing document
class RES:
    # Match at least 20 whitespace characters or at least 7 tabs, followed by # of # DOCUMENTS.
    DOCUMENT_COUNT = re.compile("( {20,}|\t{7,})(FOCUS -)? *\d* (of|OF) \d* DOCUMENTS?")
    DOCUMENT_COUNT = re.compile("\s*(FOCUS -)? *\d* (of|OF) \d* DOCUMENTS?")

    # Header meta information group match
    HEADER_META = re.compile("([\w -]*):(.*)", re.UNICODE)

    # Body meta information. This is the same as HEADER_META, but does not include
    # lower_case characters
    BODY_META = re.compile("([^0-9a-z: ]+):(.*)$", re.UNICODE)

    # End of body: a line like 'UPDATE: 2. September 2011' or 'PUBLICATION_TYPE: ...'
    BODY_END = re.compile(
        r"[^0-9a-z: ]+:.*[ -]\d{4}$|^PUBLICATION-TYPE:|^SECTION:|^LENGTH:[^:]*$|^LANGUE:[^:]*$|^RUBRIK:", re.UNICODE)
    # Copyright notice
    COPYRIGHT = re.compile("^Copyright \d{4}.*")

    VALID_PROPERTY_NAME_PARTS = re.compile("[A-Za-z][A-Za-z0-9]*")

MONTHS = dict(spring=3,
              summer=6,
              fall=9,
              winter=12,
)

WELL_KNOWN_BODY_KEYS = ["AUTOR", "RUBRIK", "L\xc4NGE", "UPDATE", "SPRACHE",
                        "PUBLICATION-TYPE", "CODE-REVUE", "AUTEUR", "RUBRIQUE",
                        "LANGUE", "DATE-CHARGEMENT", "TYPE-PUBLICATION",
                        "LONGUEUR", "LOAD-DATE"]

BODY_KEYS_MAP = {
    # LexisNexis --> Article model
    "author": "author",
    "autor": "author",
    "auteur": "author",

    "section": "section",
    "rubrique": "section",
    "rubrik": "section",
    "l\xe4nge": "length",
    "sprache": "language",
    "langue": "language",
    "language": "language",

    "longueur": "length",
    "length": "length",
    
    "titre": "title",
    
    "name": "byline"
}

def clean_property_key(key):
    key_parts = RES.VALID_PROPERTY_NAME_PARTS.findall(key)
    return key_parts[0] + "".join(k.title() for k in key_parts[1:])

def split_header(doc):
    """
    Split header from rest of articles.

    @param doc: complete lexisnexis document
    @type doc: str

    @return: [(str) representation of the header section,
              (str) representation of the body section]
    """
    header = []
    splitted = doc.split("\n")

    # Add lines to header, until document count encountered
    for i, line in enumerate(splitted):
        if RES.DOCUMENT_COUNT.match(line):
            break

        header.append(line)

    # Add rest to body
    body = "\n".join(splitted[i:])

    return "\n".join(header).strip(), body.strip()


def parse_header(header):
    """
    Parse header (given by split_header). Headers characterize themselves by
    following this pattern:

        key: value


        key: multiple \r\n
             line \r\n
             value

    @param header: representation of header (as given by split_headers)
    @type header: str

    @return: dictionary
    """
    header = header.split("\n")
    meta = collections.defaultdict(list)

    i = 0
    while i < len(header):
        mo = RES.HEADER_META.match(header[i])
        if mo:
            # key:value present. This means we arrived at a new
            # meta value.
            cur, val = mo.groups()
            meta[cur].append(val)

            i += 1
            while i < len(header) and not RES.HEADER_META.match(header[i]):
                meta[cur].append(header[i])
                i += 1

            # An integer too far!
            i -= 1

        i += 1

    # Clean values and create 'real' dict
    return {key.strip(): "\n".join(vals).strip() for key, vals in meta.items()}


def split_body(body):
    """
    Split body into multiple text pieces contaning the articles.

    @param body: representation of body
    @type body: str

    @return: generator yielding strings
    """
    art = StringIO()
    for line in body.split("\n")[1:]:
        if RES.DOCUMENT_COUNT.match(line):
            yield art.getvalue()

            art = StringIO()

        else:
            art.write(line)
            art.write("\n")

    yield art.getvalue()


def _strip_article(art):
    """
    Remove prepending and "post"pending empty lines and remove
    \r (Windows newline) characters.
    """
    art = art.split("\n")

    for i in (0, -1):
        while not art[i].strip():
            del art[i]

    return "\n".join(art).replace("\r", "")


def _is_date(string):
    try:
        toolkit.read_date(string)
    except ValueError:
        return False

    return True

def parse_online_article(art):
    # First, test for online articles with specific format
    blocks = re.split("\n *\n\s*", _strip_article(art))
    if len(blocks) != 6:
        return
    medium, url, datestr, title, nwords, lead = blocks
    if not (url.startswith("http://") or url.startswith("https://")):
        return
    if lead.startswith("Bewaar lees artikel"):
        lead = lead[len("Bewaar lees artikel"):]
    
    if not re.match("(\d+) words", nwords):
        return
    date = toolkit.read_date(datestr)
    return title.strip(), None, lead.strip(), date, medium, {"length": nwords, "url": url}

def parse_article(art):
    """
    A lexis nexis article consists of five parts:
    1) a header
    2) the title and possibly a byline
    3) a block of meta fields
    4) the body
    5) a block of meta fields

    The header consists of 'centered' lines, ie starting with a whitespace character
    The title (and byline) are left justified non-marked lines before the first meta field
    The meta fields are of the form FIELDNAME: value and can contain various field names
    The body starts after either two blank lines, or if a line is not of the meta field form.
    The body ends with a 'load date', which is of form FIELDNAME: DATE ending with a four digit year
    """

    online = parse_online_article(art)
    if online:
        return online

    
    header, title, meta, body = [], [], [], []

    header_headline = []

    def next_is_indented(lines, skipblank=True):
        if len(lines) <= 1: return False
        if not lines[1].strip():
            if not skipblank: return False
            return next_is_indented(lines[1:])
        return lines[1].startswith(" ")


    def followed_by_date_block(lines):
        # this text is followed by a date block
        # possibly, there is another line in the first block
        # (blank line)
        #          indented date line
        #          optional second indented date line
        # (blank line)
        if len(lines) < 5: return False
        if ((not lines[1].strip()) and
                lines[2].startswith(" ") and
                (not lines[3].strip())):
            return True
        if ((not lines[1].strip()) and
                lines[2].startswith(" ") and
                lines[2].startswith(" ") and
                (not lines[4].strip())):
            return True
        if not lines[1].strip(): return False
        if lines[1].startswith(" "): return False
        return followed_by_date_block(lines[1:])

    def _in_header(lines):
        if not lines: return False
        if not lines[0].strip(): return True  # blank line

        # indented line spanning page width: header
        if (not lines[0].startswith(" ")
            and next_is_indented(lines, skipblank=False)
            and len(lines[0].strip()) > 75):
            return True

        # non-indented TITLE or normal line followed by indented line
        if (not lines[0].startswith(" ")) and next_is_indented(lines):
            header_headline.append(lines.pop(0))
        else:
            while (not lines[0].startswith(" ")) and followed_by_date_block(lines):
                header_headline.append(lines.pop(0))

        # check again after possible removal of header_headline
        if not lines: return False
        if not lines[0].strip(): return True  # blank line
        if lines[0].startswith(" "): return True  # indented line


    def _get_header(lines) -> dict:
        """Consume and return all lines that are indented (ie the list is changed in place)"""
        while _in_header(lines):
            line = lines.pop(0)
            line = line.strip()
            if line:
                if re.match('Copyright \d{4}', line):
                    line = line[len('Copyright xxxx'):]
                yield line

    def _get_headline(lines):
        """Return title and byline, consuming the lines"""
        headline, byline = [], []
        target = headline

        while lines:
            line = lines[0].strip()
            if RES.BODY_META.match(line):
                return None, None
            if not line:
                # they thought of something new again...
                # title\n\nbyline\n\nLENGTH:
                # so empty line is not always the end
                if (len(lines) > 4 and (not lines[2]) and lines[1]
                    and RES.BODY_META.match(lines[3]) and (not RES.BODY_META.match(lines[1]))):
                    target = byline
                else:
                    break
            if line.endswith(";"):
                target.append(line[:-1])
                target = byline
            else:
                target.append(line)
            del lines[0]
        return (re.sub("\s+", " ", " ".join(x)) if x else None
                for x in (headline, byline))

    def _get_meta(lines) -> dict:
        """
        Return meta key-value pairs. Stop if body start criterion is found
        (eg two blank lines or non-meta line)
        """
        while lines:
            line = lines[0].strip()
            next_line = lines[1].strip() if len(lines) >= 2 else None

            meta_match = RES.BODY_META.match(line)
            if ((not bool(line) and not bool(next_line))
                or (line and not meta_match)):
                # either two blank lines or a non-meta line
                # indicate start of body, so end of meta
                break
            del lines[0]
            if meta_match:
                key, val = meta_match.groups()
                key = key.lower()
                key = BODY_KEYS_MAP.get(key, key)
                # multi-line meta: add following non-blank lines
                while lines and lines[0].strip():
                    val += " " + lines.pop(0)
                val = re.sub("\s+", " ", val)
                yield key, val.strip()


    def _get_body(lines):
        """Consume and return all lines until a date line is found"""

        while lines:
            line = lines[0].strip()
            if RES.BODY_END.match(line) or RES.COPYRIGHT.match(line):
                break  # end of body
            yield lines.pop(0)

    lines = _strip_article(art).split("\n")

    


    
    header = list(_get_header(lines))
    if not lines:
        # Something is wrong with this article, skip it
        return

    if header_headline:
        title = re.sub("\s+", " ", " ".join(header_headline)).strip()
        if ";" in title:
            title, byline = [x.strip() for x in title.split(";", 1)]
        else:
            byline = None
        if re.match("[A-Z]+:", title):
            title = title.split(":", 1)[1]
    else:
        title, byline = _get_headline(lines)

    meta = dict(_get_meta(lines))
    if title is None:
        if 'title' in meta:
            title = meta.pop('title')
        elif 'kop' in meta:
            title = meta.pop('kop')

    body = list(_get_body(lines))

    meta.update(dict(_get_meta(lines)))


    def _get_source(lines, i):
        source = lines[0 if i>0 else 1]
        if source.strip() in ("PCM Uitgevers B.V.", "De Persgroep Nederland BV") and i > 2 and lines[i-1].strip():
            source = lines[i-1]
        return source
    
    date, dateline, source = None, None, None
    for i, line in enumerate(header):
        if _is_date(line):
            date = line
            dateline = i
            source = _get_source(header, i)
    if date is None:  # try looking for only month - year notation by preprending a 1
        for i, line in enumerate(header):
            line = "1 {line}".format(**locals())
            if _is_date(line):
                date = line
                source = _get_source(header, i)
    if date is None:  # try looking for season names
        #TODO: Hack, reimplement more general!
        for i, line in enumerate(header):
            if line.strip() == "Winter 2008/2009":
                date = "2009-01-01"
                source = _get_source(header, i)


                
    def find_re_in(pattern, lines):
        for line in lines:
            m = re.search(pattern, line)
            if m: return m

    if date is None:
        yearmatch = find_re_in("(.*)(\d{4})$", header)
        if yearmatch:
            month, year = yearmatch.groups()
            month = MONTHS.get(month.replace(",", "").strip().lower(), 1)
            date = "{year}-{month:02}-01".format(**locals())
            source = header[0]
            # this is probably a journal, let's see if we can find an issue
            issuematch = find_re_in("[-\d]+[^\d]+\d+", header)
            if issuematch:
                meta['issue'] = issuematch.group(0)

        elif [x.strip() for x in header] in (["India Today"], ["Business Today"]):
            date = meta.pop("load-date")
            source = header[0]
        else:
            raise ParseError("Couldn't find date in header: {header!r}\n{art!r}".format(**locals()))

    date = toolkit.read_date(date)
    if dateline is not None and len(header) > dateline + 1:
        # next line might contain time
        timeline = header[dateline + 1]
        m = re.search(r"\b\d?\d:\d\d\s(PM\b)?", timeline)
        if m and date.time().isoformat() == '00:00:00':
            date = toolkit.read_date(" ".join([date.isoformat()[:10], m.group(0)]))

    m = re.match("copyright\s\xa9?\s?(\d{4})?(.*)", source, re.I)
    if m:
        source = m.group(2)
    source = source.strip()

    text = "\n".join(body).strip()

    if 'graphic' in meta and (not text):
        text = meta.pop('graphic')

    if title is None:
        if 'title' in meta:
            title = re.sub("\s+", " ", meta.pop('title')).strip()
            if ";" in title and not byline:
                title, byline = [x.strip() for x in title.split(";", 1)]
        else:
            title = "No title found!"

    if 'byline' in meta:
        if byline:
            title += "; %s" % byline
        byline = meta.pop('byline')

    return title.strip(), byline, text, date, source, meta


def body_to_article(title, byline, text, date, medium, meta):
    """
    Create an Article-object based on given parameters. It raises an
    error (Medium.DoesNotExist) when the given source does not have
    an entry in the database.

    @param title: headline of new Article-object
    @type title: str

    @param byline: byline for new Article
    @type byline: NoneType, str

    @param text: text for new Article
    @type text: str

    @param date: date(time) for new Article
    @type date: datetime.date, datetime.datetime

    @param source: medium-label for new Article
    @type source: str

    @param meta: object containing all sorts of meta-information, most of
                 it suitable for metastring. However, some information
                 (author, length) will be extracted.
    @type meta: dictionary

    @return Article-object

    """
    log.debug("Creating article object for {title!r}".format(**locals()))

    art = Article(title=title, text=text, date=date)

    # Author / Section
    meta = meta.copy()
    meta.pop("title", 0)
    meta.pop("text", 0)
    meta.pop("url", 0)
    meta.update(
        medium=medium,
        byline=byline
    )
    if 'url' in meta:
        art.url = meta.pop('url')
        art.url = re.sub("\s+", "", art.url)
    if 'length' in meta:
        meta['length'] = int(meta['length'].split()[0])
    properties = dict(
        length=len(art.text.split())
    )
    properties.update((clean_property_key(k), v) for k, v in meta.items() if v is not None)
    art.properties = properties
    return art


def get_query(header):
    header = {k.lower().strip(): v for k, v in header.items()}
    for key in ["zoektermen", "query", "terms"]:
        if key in header:
            return header[key]


class LexisNexis(UploadScript):
    """
    Script for importing files from Lexis Nexis. The files should be in plain text
    format with a 'cover page'. The script will extract the metadata (headline, source,
    date etc.) from the file automatically.
    """

    class options_form(UploadScript.options_form, fileupload.ZipFileUploadForm):
        pass

    name = 'Lexis Nexis'

    def split_file(self, file):
        text = "".join(file.readlines())
        header, body = split_header(text)
        self.ln_query = get_query(parse_header(header))
        fragments = list(split_body(body))
        return fragments

    def get_provenance(self, file, articles):
        # FIXME: redundant double reading of file
        provenance = super(LexisNexis, self).get_provenance(file, articles)

        if self.ln_query is None:
            return provenance

        return "{provenance}; LexisNexis query: {self.ln_query!r}".format(**locals())

    def parse_document(self, text):
        fields = parse_article(text)

        if fields is None:
            return

        try:
            a = body_to_article(*fields)
            a.project = self.options['project']
            yield a
        except:
            log.error("Error on processing fields: {fields}".format(**locals()))
            raise

