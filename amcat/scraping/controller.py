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
Module for controlling scrapers
"""
from amcat.tasks import run_scraper, LockHack
from amcat.models.article import Article

from celery import group
import logging;log = logging.getLogger(__name__)

class Controller(object):
    def run(self, scrapers):
        if not hasattr(scrapers, '__iter__'):
            scrapers = [scrapers]

        for i,scraper in enumerate(scrapers):
            scraper._id = i
            log.info("Running scraper {scraper._id}: {scraper.__class__.__name__}".format(**locals()))
            scraper.opener.cookiejar._cookies_lock = LockHack()
        task = group([run_scraper.s(scraper) for scraper in scrapers])
        result = task.apply_async()

        for scraper, articles in result.iterate():
            articles = [inner for outer in articles for inner in outer]
            log.info("Scraper {scraper._id}, {scraper.__class__.__name__}, returned {n} articles".format(n = len(articles), **locals()))
            scraper.articleset.add_articles(articles)
            yield (scraper,articles)
        
def save_ordered(articles):
    queue = [a for a in articles if a.parent == None]
    for article in queue:
        saved = Article.create_articles([article])
        #get children, add to queue
        for child in articles:
            if child.parent == article and child != parent: #...
                child.parent = saved
                queue.append(child)
    #safety measure
    for article in articles:
        if article not in queue:
            Article.create_articles([article])
    log.info("saved {n} articles".format(n = len(articles)))
    return articles
