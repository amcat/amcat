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
Base module for article upload scripts

TODO: merge this with scraper base
"""

from amcat.scripts import script
from amcat.scripts.types import ArticleIterator

from amcat.models.article import Article

from amcat.scraping.scraper import ScraperForm, Scraper

class ParseError(Exception):
    pass

class UploadScript(Scraper):
    """Base class for Upload Scripts, which are scraper scripts driven by the
    the script input.

    For legacy reasons, parse_document and split_text may be used instead of the standard
    get_units and scrape_unit.
    """
    
    input_type = unicode
    output_type = ArticleIterator
    options_form = ScraperForm
    
    def run(self, input):
        assert(isinstance(input, unicode))
        self.input_text = input
        super(UploadScript, self).run(input)
        return self.articleset


    def _get_units(self):
        return self.split_text(self.input_text)

    def _scrape_unit(self, unit):
        result =  self.parse_document(unit)
        if isinstance(result, Article):
            result = [result]
        return result
        
    def parse_document(self, document):
        """
        Parse the document as one or more articles, provided for legacy purposes

        @param document: object received from split_text, e.g. a string fragment
        @return: None, an Article or a sequence of Article(s)
        """
        raise NotImplementedError()

    def split_text(self, text):
        """
        Split the text into one or more fragments representing individual documents.

        @type text: unicode string
        @return: a sequence of objects (e.g. strings) to pass to parse_documents
        """
        return [text]
