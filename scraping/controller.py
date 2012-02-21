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

from amcat.tools.multithread import distribute_tasks, QueueProcessorThread, add_to_queue_action
import logging; log = logging.getLogger(__name__)

class Controller(object):
    """
    Controller class

    A Controller must define a scrape(scraper) method that controls the
    scraping by that scraper
    """

    def __init__(self, project, articleset=None):
        self.project = project
        self.articleset = articleset
    
    def scrape(self, scraper):
        """Run the given scraper using the control logic of this controller"""
        raise NotImplementedError()

    def save(self, article):
        log.info("Saving article %s" % article)
        #import time; time.sleep(0.3)
        article.project = self.project
        article.save()
        if self.articleset:
            self.articleset.articles.add(article)
            self.articleset.save()

class SimpleController(Controller):
    """Simple implementation of Controller"""
    def scrape(self, scraper):
        for unit in scraper.get_units():
            for article in scraper.scrape_unit(unit):
                self.save(article)


class ThreadedController(Controller):
    """Threaded implementation of Controller

    Uses multithread to distribute units over threads, and sets up a committer
    task to save the documents.
    """
    def __init__(self, project, articleset=None, nthreads=4):
        super(ThreadedController, self).__init__(project, articleset)
        self.nthreads = nthreads

    def scrape_to_queue(self, scraper, queue):
        """
        Start and join the multithreaded processing of the scraper,
        placing resulting documents on the given queue for saving
        """
        distribute_tasks(tasks=scraper.get_units(), action=scraper.scrape_unit,
                         nthreads=self.nthreads, retry_exceptions=3,
                         output_action=add_to_queue_action(queue))
        
        
    def scrape(self, scraper):
        qpt = QueueProcessorThread(self.save, name="Storer")
        qpt.start()
        self._scrape_to_queue(scraper, qpt.input_queue)
        qpt.input_queue.done=True
        qpt.input_queue.join()
   

    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest, amcatlogging
from amcat.scraping.scraper import Scraper
from amcat.models.article import Article
from datetime import date
from django.db import transaction
                
class _TestScraper(Scraper):
    def __init__(self, medium=None, n=10):
        self.n = n
        self.medium = medium or amcattest.create_test_medium()
    def get_units(self):
        return range(self.n)
    def scrape_unit(self, unit):
        yield Article(headline=str(unit), date=date.today(), medium=self.medium)
                
class TestController(amcattest.PolicyTestCase):
    def test_scraper(self):
        """Does the simple controller and saving work?"""
        p = amcattest.create_test_project()
        c = SimpleController(p)
        ts = _TestScraper()
        c.scrape(ts)
        self.assertEqual(p.articles.count(), ts.n)
        
    def test_set(self):
        """Are scraped articles added to the set?"""
        p = amcattest.create_test_project()
        s = amcattest.create_test_set()
        c = SimpleController(p, s)
        ts = _TestScraper()
        c.scrape(ts)
        self.assertEqual(p.articles.count(), ts.n)
        self.assertEqual(s.articles.count(), ts.n)

    def test_threaded(self):
        """Does the threaded controller and saving work?"""
        p = amcattest.create_test_project()
        from Queue import Queue
        q = Queue()
        c = ThreadedController(p)
        ts = _TestScraper()
        # Multithreaded saving does not work in unit test, so save in-thread
        # See below for a 'production test'
        c._scrape_to_queue(ts, q)
        while not q.empty():
            c.save(q.get())
        self.assertEqual(p.articles.count(), ts.n)

def production_test_multithreaded_saving():
    """
    Test whether multithreaded saving works.
    Threaded commit does not work in unit test, code below actually creates
        projects and articles, so run on test database only!
    """
    from amcat.models.medium import Medium
    from amcat.models.project import Project
    import threading
    p = Project.objects.get(pk=2)
    s = amcattest.create_test_set(project=p)
    log.info("Created article set {s.id}".format(**locals()))
    c = ThreadedController(p, s)
    ts = _TestScraper(medium=Medium.objects.get(pk=1))
    c.scrape(ts)
    if s.articles.count() == ts.n:
        log.info("[OK] Production test Multithreaded Saving passed")
    else:
        raise Exception("#Scraped articles incorrect, expected {ts.n}, received {n}"
                        .format(n=s.articles.count(), **locals()))
    
if __name__ == '__main__':
    production_test_multithreaded_saving()
