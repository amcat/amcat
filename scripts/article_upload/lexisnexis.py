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

from amcat.scripts.article_upload.upload import UploadScript, ParseError

from amcat.tools import toolkit

from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tools.djangotoolkit import get_or_create

import re
import collections
import StringIO

import logging; log = logging.getLogger(__name__)

# Regular expressions used for parsing document
RES = {
    # Match at least 20 whitespace characters, followed by # of # DOCUMENTS.
    "DOCUMENT_COUNT" : re.compile(" {20} +\d* of \d* DOCUMENTS"),

    # Header meta information group match
    "HEADER_META" : re.compile("([\w -]*):(.*)", re.UNICODE),

    # Body meta information. This is the same as HEADER_META, but does not include
    # lower_case characters.
    "BODY_META" : re.compile("([^0-9a-z: ]*):(.*[^;])$", re.UNICODE),

    # Copyright notice
    "COPYRIGHT" : re.compile("^Copyright \d{4}.*")
}

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



class LexisNexis(UploadScript):
    """
    Script for importing files from Lexis Nexis. The files should be in plain text
    format with a 'cover page'. The script will extract the metadata (headline, source,
    date etc.) from the file automatically.
    """

    name = 'Lexis Nexis'

    def split_header(self, doc):
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
            if RES["DOCUMENT_COUNT"].match(line):
                break

            header.append(line)

        # Add rest to body
        body = "\n".join(splitted[i:])

        return "\n".join(header).strip(), body.strip()

    def parse_header(self, header):
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
            mo = RES["HEADER_META"].match(header[i])
            if mo:
                # key:value present. This means we arrived at a new
                # meta value.
                cur, val = mo.groups()
                meta[cur].append(val)

                i += 1
                while i < len(header) and not RES["HEADER_META"].match(header[i]):
                    meta[cur].append(header[i])
                    i += 1

                # An integer too far!
                i -= 1

            i += 1

        # Clean values and create 'real' dict
        return dict([(key.strip(), "\n".join(vals).strip()) for key, vals in meta.items()])

    def split_body(self, body):
        """
        Split body into multiple text pieces contaning the articles.

        @param body: representation of body
        @type body: unicode / str

        @return: generator yielding unicode strings
        """
        art = StringIO.StringIO()
        for line in body.split("\n")[1:]:
            if RES["DOCUMENT_COUNT"].match(line):
                yield art.getvalue()

                art = StringIO.StringIO()

            else:
                art.write(line)
                art.write("\n")

        yield art.getvalue()

    def _strip_article(self, art):
        """
        Remove prepending and "post"pending empty lines and remove
        \r (Windows newline) characters.
        """
        art = art.split("\n")

        for i in (0, -1):
            while not art[i].strip():
                del art[i]

        return "\n".join(art).replace("\r", "")

    def _is_date(self, string):
        try:
            toolkit.readDate(string)
        except ValueError:
            return False

        return True



    def parse_article(self, art):
        """
        The most 'interesting' method :-). Parses a piece of text containing
        an article.

        @param art: article to parse
        @type art: unicode / str

        @return headline, byline, text, date, source, meta
        """
        # Store unidentified text pieces here to identify (guess)
        # them later. Indented texts usually contain the magazine
        # name and date, non-indented chunks the headline and text.
        #
        # Copyright notice might be in one of both, but will be
        # ignored.
        uit = []
        uit_indented = []
        meta = {}
        byline = None

        i = 0; art = self._strip_article(art).split("\n")
        while i < len(art):
            line = art[i]

            # Determine if this line contains meta-data
            mo = RES["BODY_META"].match(line)
            if mo:
                key, val = mo.groups()
                key = key.lower()
                key = BODY_KEYS_MAP.get(key, key)
                meta[key] = val.strip()
            elif line.strip():
                # Unidentified text found!
                if art[i+1].strip():
                    # Multiple line text found. Enter 'greedy' mode (only
                    # stop when meta-data found)
                    ut = []

                    # Before traversing downwards, traverse upwards, to include
                    # all uit text until a BODY_META is found.
                    j = i - 1;
                    while (j >= 0 and not RES["BODY_META"].match(art[j])
                           and not art[j].startswith(' ')):
                        if art[j].strip() in uit:
                            del uit[uit.index(art[j])]

                        ut.insert(0, art[j])
                        j -= 1

                    # Now traverse downwards
                    while i < len(art) and not RES["BODY_META"].match(art[i]):
                        ut.append(art[i])
                        i += 1

                    i -= 1
                    uit.append("\n".join(ut).strip())

                elif line.startswith(' '):
                    uit_indented.append(line.strip())
                else:
                    uit.append(line.strip())

            i += 1

        # Get date and source
        ui = uit_indented
        if self._is_date(ui[0]):
            date = toolkit.readDate(ui[0])
            source = ui[1]
        elif self._is_date(ui[1]):
            date = toolkit.readDate(ui[1])
            source = ui[0]
        else:
            raise ParseError("Couldn't find date in '{0}' or '{1}'".format(*ui[:3]))


        # Get text and headline
        uit.sort(key=len)
        headline = None

        for text in uit[:-1]:
            splitted = text.split('\n')

            # Text with headline and byline end its (first) line with ';'
            for i, line in enumerate(splitted):
                if splitted[i].endswith(';'):
                    headline = " ".join(splitted[:i+1])[:-1]
                    byline = "\n".join(splitted[1:])
                    break

        # Headline not found? Assign first uit text withouth
        # an '\n'
        if headline is None:
            for t in uit[:-1]:
                if "\n" not in t:
                    headline = t
                    break

        # Headline still not found? Get first not-well known body key
        #if headline is None:
        #    for key in meta.keys():
        #        if key not in WELL_KNOWN_BODY_KEYS:
        #            headline = u"%s: %s" % (key, meta[key])
        #            del meta[key]

        # Least-reliable method, choose the smallest element in
        # uit which does matches the copyright regular expression,
        # as it is probably the headline
        if headline is None:
            for ui in uit[0:-1]:
                if not RES["COPYRIGHT"].match(ui):
                    headline = ui
                    break

        if headline is None:
            headline = "No headline found!"

        # Get text, the biggest element in uit
        text = uit[-1]
        return headline.strip(), byline, text, date, source, meta

    def body_to_article(self, headline, byline, text, date, source, meta):
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
        art = Article(headline=headline, byline=byline, text=text, date=date)


        art.medium = get_or_create(Medium, name=source)


        # Author / Section
        meta = meta.copy()
        art.author = meta.pop('author', None)
        art.section = meta.pop('section', None)
        art.length = int(meta.pop('length').split()[0])
        art.metastring = str(meta)

        art.project = self.options['project']

        return art

    def split_text(self, text):
        header, body = self.split_header(text)
        header = self.parse_header(header)

        return self.split_body(body)

    def parse_document(self, text):
        fields = self.parse_article(text)
        try:
            return self.body_to_article(*fields)
        except:
            log.error("Error on processing fields: {fields}".format(**locals()))
            raise

    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(handle_output=False)


