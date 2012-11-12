# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import
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

from urllib import quote_plus, unquote_plus
from urllib2 import HTTPError

INDEX_URL = "https://www.google.com/search?num=100&q={}&start={}"

from amcat.scraping.document import HTMLDocument
from amcat.scraping.scraper import HTTPScraper

class GoogleScraper(HTTPScraper):
    query=""
    article_url_pattern=""

    def __init__(self,*args,**kwargs):
        super(GoogleScraper,self).__init__(*args,**kwargs)
        self.query = quote_plus(self.query)

    def _get_units(self):
        """checks for http errors before yielding, and therefore yields the document along with the url
        for a double request would be a waste of time"""



        self.query = quote_plus(self.query)
        start = 0
        index_url = INDEX_URL.format(self.query,start)
        index = self.getdoc(index_url) 
        while index.cssselect("#rso li.g"):
            for unit in index.cssselect('#rso li.g'):
                href = unit.cssselect('a.l')[0].get('href')
                if self.article_url_pattern.search(href):
                    doc = HTMLDocument(url=href)
                    try:
                        doc.prepare(self)
                    except HTTPError as e:
                        print(e)
                        continue
                    else:
                        yield doc
            start += 100
            index_url = INDEX_URL.format(self.query,start)
            index = self.getdoc(index_url)


