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
Plugin for uploading pdf files of a certain markup, provided by BZK
"""

from __future__ import unicode_literals, absolute_import

from amcat.scripts.article_upload.upload import UploadScript
from amcat.scraping.document import Document
from amcat.scraping.pdf import PDFScraper
from amcat.models.medium import Medium
from amcat.scripts.article_upload.bzk_aliases import BZK_ALIASES as MEDIUM_ALIASES

from datetime import date
import re

class BZKPDFScraper(PDFScraper, UploadScript):

    def _get_units(self):
        yield self.doc
        
    def _scrape_unit(self, unit):
        self.index = []
        article_lines = []
        headline = ""
        for i, p in enumerate(self.process_document(self.doc)):
            
            index_pattern = re.compile("^[^\(]+\([^\)]+\)..+[0-9]+$")
            if any([index_pattern.match(line.get_text()) for line in self.get_textlines(p)]):
                for line in self.get_textlines(p):
                    pattern = re.compile("([^\(]+)(\([0-9]+\))? \(([^\)]+)\).+")
                    text = line.get_text()
                    result = pattern.search(text)
                    if result:
                        h = result.group(1); m = result.group(3)
                        self.index.append((h, m))
                continue



            for line in self.get_textlines(p):
                text = line.get_text()
                if text.lower().strip() in [i[0].lower().strip() for i in self.index]:

                    # title is recognized. yield old article, start new
                    if len(headline) > 0:
                        article =  self.getarticle(headline, article_lines)
                        yield article
                        

                    headline = text
                    article_lines = []
                                
                article_lines.append(text)
                
            #last article
            yield self.getarticle(headline, article_lines)
                        
    def getarticle(self, headline, lines):
        article = Document(headline = headline)
        text = ""
        for line in lines[2:]:
            if len(line) > 2:
                text += "\n" + line

        text = text.replace("-\n","")
        text = text.replace("  "," ")
        text = text.replace("\n"," ")

        article.props.text = text
        date_pattern = re.compile("([0-9]{2,2})\-([0-9]{2,2})\-([0-9]{4,4})")
        result = date_pattern.search(lines[1])
        article.props.date = date(
            int(result.group(3)),
            int(result.group(2)),
            int(result.group(1)))
        pagenum_pattern = re.compile("\(p.([0-9]+)([0-9\-]+)?\)")
        result = pagenum_pattern.search(lines[1])
        if result:
            
            article.props.pagenr = int(result.group(1))

        for h, medium in self.index:
            if article.props.headline.lower().strip() in h.lower().strip():
                article.props.medium = self.create_medium(medium)

        return article

    def create_medium(self, medium):
        if not medium or len(medium) < 1:
            medium = "unknown"
        if medium in MEDIUM_ALIASES.keys():
            return Medium.get_or_create(MEDIUM_ALIASES[medium])
        else:
            return Medium.get_or_create(medium)

if __name__ == "__main__":
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.scraping")
    from amcat.scripts.tools import cli
    cli.run_cli(BZKPDFScraper)

