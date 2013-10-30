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
import cPickle as pickle
from celery import group
import logging;log = logging.getLogger(__name__)

class Controller(object):
    def run(self, scrapers):
        if not hasattr(scrapers, '__iter__'):
            scrapers = [scrapers]

        for i, scraper in enumerate(scrapers):
            scraper._id = i
            if hasattr(scraper, 'opener'):
                scraper.opener.cookiejar._cookies_lock = LockHack()

        subtasks = []
        for scraper in scrapers:
            log.debug("checking pickle for {scraper}".format(**locals()))
            try:
                pickle.dumps(scraper)
            except (pickle.PicklingError, TypeError):
                log.exception("Picking {scraper} failed".format(**locals()))
            else:
                subtasks.append(run_scraper.s(scraper))
                
        task = group(subtasks)
        result = task.apply_async()

        for scraper, articles in result.iterate():
            articles = [inner for outer in articles for inner in outer] #[[a,b][c,d]] -> [a,b,c,d]
            log.info("Scraper {scraper._id}, {scraper.__class__.__name__}, returned {n} articles".format(
                    n = len(articles), **locals()))
            yield (scraper,articles)
