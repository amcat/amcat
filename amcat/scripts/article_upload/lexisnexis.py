#!/usr/bin/python
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
This module contains a (semi-machine readable) lexisnexis parser.
"""

from __future__ import unicode_literals

from amcat.scripts.article_upload.upload import UploadScript, UploadForm, ParseError

from amcat.tools import toolkit

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools.djangotoolkit import get_or_create

import re, os.path
import collections
import StringIO
from itertools import takewhile, count
from string import strip

import logging; log = logging.getLogger(__name__)

# Regular expressions used for parsing document
class RES:
    # Match at least 20 whitespace characters, followed by # of # DOCUMENTS.
    DOCUMENT_COUNT = re.compile(" {20} +\d* of \d* DOCUMENT")

    # Header meta information group match
    HEADER_META = re.compile("([\w -]*):(.*)", re.UNICODE)

    # Body meta information. This is the same as HEADER_META, but does not include
    # lower_case characters.
    BODY_META = re.compile("([^0-9a-z: ]+):(.*[^;])$", re.UNICODE)

    # End of body: a line like 'UPDATE: 2. September 2011' or 'PUBLICATION_TYPE: ...'
    BODY_END = re.compile(r"[^0-9a-z: ]+:.*[ -]\d{4}$|^PUBLICATION-TYPE:", re.UNICODE)
    # Copyright notice
    COPYRIGHT = re.compile("^Copyright \d{4}.*")


WELL_KNOWN_BODY_KEYS = ["AUTOR", "RUBRIK", "L\xc4NGE", "UPDATE", "SPRACHE",
                        "PUBLICATION-TYPE", "CODE-REVUE", "AUTEUR", "RUBRIQUE",
                        "LANGUE", "DATE-CHARGEMENT", "TYPE-PUBLICATION",
                        "LONGUEUR", "LOAD-DATE"]

BODY_KEYS_MAP = {
    # LexisNexis --> Article model
    "autor" : "author",
    "rubrik" : "section",
    "l\xe4nge" : "length",
    "sprache" : "language",
    "auteur" : "author",
    "rubrique" : "section",
    "langue" : "language",
    "longueur" : "length",
    "length" : "length",
    "language" : "language",
    "section" : "section",
    "author" : "author"
}




def split_header(doc):
    """
    Split header from rest of articles.

    @param doc: complete lexisnexis document
    @type doc: unicode

    @return: [(unicode) representation of the header section,
              (unicode) representation of the body section]
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
    @type header: unicode / str

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
    return {key.strip() : "\n".join(vals).strip() for key, vals in meta.items()}

def split_body(body):
    """
    Split body into multiple text pieces contaning the articles.

    @param body: representation of body
    @type body: unicode / str

    @return: generator yielding unicode strings
    """
    art = StringIO.StringIO()
    for line in body.split("\n")[1:]:
        if RES.DOCUMENT_COUNT.match(line):
            yield art.getvalue()

            art = StringIO.StringIO()

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
        toolkit.readDate(string)
    except ValueError:
        return False

    return True


def parse_article(art):
    """
    A lexis nexis article consists of five parts:
    1) a header
    2) the headline and possibly a byline
    3) a block of meta fields
    4) the body
    5) a block of meta fields

    The header consists of 'centered' lines, ie starting with a whitespace character
    The headline (and byline) are left justified non-marked lines before the first meta field
    The meta fields are of the form FIELDNAME: value and can contain various field names
    The body starts after either two blank lines, or if a line is not of the meta field form.
    The body ends with a 'load date', which is of form FIELDNAME: DATE ending with a four digit year
    """

    header, headline, meta, body = [], [], [], []


    @toolkit.to_list
    def _get_header(lines):
        """Consume and return all lines that are indented (ie the list is changed in place)"""
        while lines and ((not lines[0].strip()) or lines[0].startswith(" ")):
            line = lines.pop(0)
            if line:
                if line.strip().startswith('Copyright '):
                    # skip lines until a blank line is found
                    while lines and line.strip():
                        line = lines.pop(0)
                else:
                    yield line

    def _get_headline(lines):
        """Return headline and byline, consuming the lines"""
        headline, byline = [], []
        target = headline

        while lines:
            line = lines[0].strip()
            if RES.BODY_META.match(line):
                return None, None
            if not line:
                break
            if line.endswith(";"):
                target.append(line[:-1])
                target = byline
            else:
                target.append(line)
            del lines[0]
        return (re.sub("\s+", " ", " ".join(x)) if x else None
                for x in (headline, byline))

    @toolkit.wrapped(dict)
    def _get_meta(lines):
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


    @toolkit.to_list
    def _get_body(lines):
        """Consume and return all lines until a date line is found"""

        while lines:
            line = lines[0].strip()
            if RES.BODY_END.match(line) or RES.COPYRIGHT.match(line):
                break # end of body                
            yield lines.pop(0)

    lines = _strip_article(art).split("\n")
    header = _get_header(lines)
    if not lines:
        # Something is wrong with this article, skip it
        return

    headline, byline = _get_headline(lines)
    meta = _get_meta(lines)
    body = _get_body(lines)
    meta.update(_get_meta(lines))

    date = None
    for i, line in enumerate(header):
        if _is_date(line):
            date = line
            source = header[0 if i > 0 else 1]
    if date is None: # try looking for only month - year notation by preprending a 1
        for i, line in enumerate(header):
            line = "1 {line}".format(**locals())
            if _is_date(line):
                date = line
                source = header[0 if i > 0 else 1]
    if date is None: # try looking for season names
        #TODO: Hack, reimplement more general!
        for i, line in enumerate(header):
            if line.strip() == "Winter 2008/2009":
                date = "2009-01-01"
                source = header[0 if i > 0 else 1]
    if date is None:
        raise ParseError("Couldn't find date in header: {header!r}".format(**locals()))

    date = toolkit.readDate(date)
    source = source.strip()

    text = "\n".join(body).strip()

    if 'graphic' in meta and (not text):
        text = meta.pop('graphic')

    if headline is None:
        if 'title' in meta:
            headline = meta.pop('title')
        else:
            headline = "No headline found!"

    if 'byline' in meta:
        if byline:
            headline += "; %s" % byline
        byline = meta.pop('byline')


    return headline.strip(), byline, text, date, source, meta

def body_to_article(headline, byline, text, date, source, meta):
    """
    Create an Article-object based on given parameters. It raises an
    error (Medium.DoesNotExist) when the given source does not have
    an entry in the database.

    @param headline: headline of new Article-object
    @type headline: unicode / str

    @param byline: byline for new Article
    @type byline: NoneType, unicode, str

    @param text: text for new Article
    @type text: unicode / str

    @param date: date(time) for new Article
    @type date: datetime.date, datetime.datetime

    @param source: medium-label for new Article
    @type source: unicode / str

    @param meta: object containing all sorts of meta-information, most of
                 it suitable for metastring. However, some information
                 (author, length) will be extracted.
    @type meta: dictionary

    @return Article-object

    """
    log.debug("Creating article object for {headline!r}".format(**locals()))

    art = Article(headline=headline, byline=byline, text=text, date=date)


    art.medium = get_or_create(Medium, name=source)


    # Author / Section
    meta = meta.copy()
    art.author = meta.pop('author', None)
    art.section = meta.pop('section', None)
    if 'length' in meta:
        art.length = int(meta.pop('length').split()[0])
    else:
        art.length = art.text.count(" ")
    art.metastring = str(meta)

    return art

def get_query(header):
    header = {k.lower().strip() : v for k,v in header.iteritems()}
    for key in ["zoektermen", "query", "terms"]:
        if key in header:
            return header[key]


class LexisNexis(UploadScript):
    """
    Script for importing files from Lexis Nexis. The files should be in plain text
    format with a 'cover page'. The script will extract the metadata (headline, source,
    date etc.) from the file automatically.
    """

    name = 'Lexis Nexis'

    def _prepare_file(self, file):
        """
        Split the file into header and body and annotate the file object with _ln_header and _ln_body
        """
        if hasattr(file, '_ln_body'):
            return
        text = self.decode(file.read())
        file._ln_header, file._ln_body = split_header(text) 

    
    def split_file(self, file):
        self._prepare_file(file)
        fragments = list(split_body(file._ln_body))
        return fragments

    def get_provenance(self, file, articles):
        # FIXME: redundant double reading of file
        provenance = super(LexisNexis, self).get_provenance(file, articles)
        
        self._prepare_file(file)
        header = parse_header(file._ln_header)
        q = get_query(header)
        if q is None: return provenance
        
        return "{provenance}; LexisNexis query: {q!r}".format(**locals())
    
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

from amcat.tools import amcatlogging; amcatlogging.debug_module()
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(handle_output=False)



###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest
import datetime

class TestLexisNexis(amcattest.PolicyTestCase):
    def setUp(self):
        import os.path, json
        self.dir = os.path.join(os.path.dirname(__file__), 'test_files', 'lexisnexis')

        self.test_text = open(os.path.join(self.dir, 'test.txt')).read().decode('utf-8')
        self.test_text2 = open(os.path.join(self.dir, 'test2.txt')).read().decode('utf-8')

        self.test_body_sols = json.load(open(os.path.join(self.dir, 'test_body_sols.json')))
        self.test_header_sols = json.load(open(os.path.join(self.dir, 'test_header_sols.json')))


        
    def split(self):
        return split_header(self.test_text)

    def test_split_header(self):
        splitted = self.split()

        self.assertEquals(len(splitted[0]), 438)

    def test_split_body(self):
        splitted = self.split()

        n_found = len(list(split_body(splitted[1])))
        n_sol = len(self.test_body_sols)
        
        self.assertEquals(n_found, n_sol + 1) # +1 for 'defigured' article

    def test_parse_header(self):
        splitted = self.split()

        self.maxDiff = None
        meta = parse_header(splitted[0])
        self.assertEquals(meta, self.test_header_sols)

    def test_parse_article(self):
        splitted = self.split()
        texts = split_body(splitted[1])
        
        # Json doesn't do dates
        arts = []
        
        for a in texts:
            art = parse_article(a)
            if art is not None:
                art = list(art)
                art[3] = str(art[3])
                arts.append(art)

        # Tests..
        self.assertEquals(len(arts), len(self.test_body_sols))

        for i, art in enumerate(self.test_body_sols):
            self.assertEquals(art, arts[i])

    def _create_medium(self, source):
        from amcat.models import Language
        try:
            Medium.objects.get(name__iexact=source)
        except Medium.DoesNotExist:
            l = Language.objects.get(id=1)
            Medium(name=source, abbrev=source[0:5], circulation=1, language=l).save()

    def test_meta(self):

        a = list(split_body(self.split()[1]))[0]
        meta = parse_article(a)[-1]
        self.assertEqual(meta.pop('length').split()[0], "306")

    def test_body_to_article(self):
        header, body = self.split()
        articles = split_body(body)
        articles = [parse_article(a) for a in articles]

        # Only testing the first article. If this contains correct
        # data, we assume the implementation is correct. However,
        # we do test the remaining articles with full_clean().

        art = body_to_article(*articles[0])
        self.assertEquals(art.length, 306)
        self.assertEquals(art.headline, "This is a headline")
        self.assertEquals(art.byline, "with a byline. The article contains unicode characters.")
        self.assertEquals(art.text, articles[0][2])
        self.assertEquals(art.date, datetime.datetime(2011, 8, 31))
        self.assertEquals(art.medium.name, u"B\u00f6rsen-Zeitung")
        self.assertEquals(art.author, "MF Tokio")
        self.assertEquals(eval(art.metastring), {u'update': u'2. September 2011',
                                                 u'language': u'GERMAN; DEUTSCH',
                                                 u'publication-type': u'Zeitung'})

        # Setup environment
        dp = amcattest.create_test_project()

        # Test remaining articles
        for art in articles[1:]:
            if art is None: continue
            self._create_medium(art[4])

            p = body_to_article(*art)
            p.project = dp
            p.full_clean()

    def test_get_query(self):
        header, body =  split_header(self.test_text)
        q = get_query(parse_header(header))
        query = (u'(((Japan OR Fukushima) AND (Erdbeben OR nuklear OR Tsunami OR Krise\nOR Katastrophe OR Tepco)) '
                 ' AND date(geq(7/3/2011) AND leq(31/8/2011)) AND\n'
                 'pub(B\xf6rsen Zeitung OR  Frankfurter Rundschau OR  taz OR  die tageszeitung))')
        self.assertEqual(q, query)

        header, body =  split_header(self.test_text2)
        q = get_query(parse_header(header))
        self.assertIsNone(q)
        
    def test_parse_no_header(self):
        header, body =  split_header(self.test_text2)
        header = header.replace(u'\ufeff', '').strip()
        self.assertFalse(bool(header))

        n_found = len(list(split_body(body)))
        self.assertEqual(n_found, 1)

    def test_provenance(self):
        import os.path
        from django.core.files import File
        articleset = amcattest.create_test_set()
        ln =  LexisNexis(project=amcattest.create_test_project().id,
                         file=File(open(os.path.join(self.dir, 'test.txt'))),
                         articleset=articleset.id)

        arts = ln.run()
        self.assertEqual(len(arts), len(self.test_body_sols))
        self.assertIn("LexisNexis query: u'(((Japan OR Fukushima)", ln.articleset.provenance)

        articleset = amcattest.create_test_set()
        ln =  LexisNexis(project=amcattest.create_test_project().id,
                         file=File(open(os.path.join(self.dir, 'test2.txt'))),
                         articleset=articleset.id)

        arts = ln.run()
        # no query so provenance is the 'standard' message
        self.assertTrue(ln.articleset.provenance.endswith("test2.txt' using LexisNexis"))
