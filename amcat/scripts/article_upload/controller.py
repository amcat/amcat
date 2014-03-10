from __future__  import absolute_import
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
Module for running scrapers
"""

import logging;log = logging.getLogger(__name__)
from collections import namedtuple

from amcat.models import Article, Project

ScrapeError = namedtuple("ScrapeError", ["i", "unit", "error"])

class Controller(object):
    def __init__(self):
        self.errors = []
        self.articles = []

    def run(self, scraper):
        try:
            units = list(scraper._get_units())
        except Exception as e:
            self.errors.append(ScrapeError(None,None,e))
            log.exception("scraper._get_units failed")
            return self.articles

        for i, unit in enumerate(units):
            try:
                articles = list(scraper._scrape_unit(unit))
            except Exception as e:
                log.exception("scraper._scrape_unit failed")
                self.errors.append(ScrapeError(i,unit,e))
                continue
            self.articles += articles

        for article in self.articles:
            _set_default(article, 'project', scraper.project)

        try:
            articles, errors = Article.create_articles(self.articles, scraper.articleset)
            self.saved_article_ids = {getattr(a, "duplicate_of", a.id) for a in self.articles}
            for e in errors:
                self.errors.append(ScrapeError(None,None,e))
        except Exception as e:
            self.errors.append(ScrapeError(None,None,e))
            log.exception("scraper._get_units failed")

        return self.saved_article_ids

def _set_default(obj, attr, val):
    try:
        if getattr(obj, attr, None) is not None: return
    except Project.DoesNotExist:
        pass # django throws DNE on x.y if y is not set and not nullable
    setattr(obj, attr, val)
