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

import logging; log = logging.getLogger(__name__)
from cStringIO import StringIO

from amcat.tools.toolkit import to_list, retry
from amcat.tools.multithread import distribute_tasks, QueueProcessorThread, add_to_queue_action
from amcat.tools import amcatlogging
from amcat.models import ArticleSet

from amcat.scripts.maintenance.deduplicate import DeduplicateScript

from django.db import transaction, DatabaseError, IntegrityError


class Controller(object):
    """
    Controller class

    A Controller must define a scrape(scraper) method that controls the
    scraping by that scraper
    """

    def __init__(self, articleset=None):
        self.articleset = articleset

    def scrape(self, scrapers, deduplicate=False):
        """Run the given scraper using the control logic of this controller"""
        used_sets, all_articles= set(), set()
        try:
            scrapers = iter(scrapers)
        except TypeError:
            scrapers = [scrapers]
            
        for scraper in scrapers:
            try:
                articles = self._scrape(scraper)
            except Exception:
                log.exception("failed scraping {scraper}".format(**locals()))
                continue
            scraper.articleset.add_articles(articles, set_dirty=False)
            all_articles |= set(articles)
            used_sets.add(scraper.articleset.id)

            if deduplicate == True:                
                options = {
                    'articleset' : scraper.articleset.id,
                    }
                if 'date' in scraper.options.keys():
                    options['first_date'] = scraper.options['date']
                    options['last_date'] = scraper.options['date']

                DeduplicateScript(**options).run(None)

        ArticleSet.objects.filter(pk__in=used_sets).update(index_dirty=True)
        return all_articles

    def save(self, article):
        log.debug("Saving article %s" % article)
        try:
            save = transaction.savepoint()
            article.save()
        except (IntegrityError, DatabaseError):
            log.exception("saving article {article} failed".format(**locals()))
            transaction.savepoint_rollback(save)
            return

        log.debug("Done")
        return article

class SimpleController(Controller):
    """Simple implementation of Controller"""
    
    @to_list
    def _scrape(self, scraper):
        result = []
        units = scraper.get_units()
        for unit in units:
            for article in scraper.scrape_unit(unit):
                result.append(self.save(article))
        return result
   


class RobustController(Controller):
    """More robust implementation of Controller with sensible transaction management"""

    def _scrape(self, scraper):
        log.info("RobustController starting scraping for scraper {}".format(scraper))
        result = []
        for unit in scraper.get_units():
            try:
                for article in self.scrape_unit(scraper, unit):
                    result.append(article)
            except Exception as e:
                log.exception("exception within get_units")

        log.info("Scraping %s finished, %i articles" % (scraper, len(result)))

        if not result:
            raise Exception("No results returned by _get_units()")

        log.info("adding articles to set {scraper.articleset.id}".format(**locals()))
        return result

    def scrape_unit(self, scraper, unit):
        try:
            scrapedunits = list(scraper.scrape_unit(unit))
        except Exception:
            log.exception("exception within scrape_unit")
            return

        if len(scrapedunits) == 0:
            log.warning("scrape_unit returned 0 units")
        
        for unit in scrapedunits:
            try: #can go wrong, will go wrong
                log.info("saving unit {unit}".format(**locals()))
            except Exception:
                log.exception("log.info failed")
            unit = self.save(unit)
            if unit:
                yield unit
        


class ThreadedController(Controller):
    """Threaded implementation of Controller

    Uses multithread to distribute units over threads, and sets up a committer
    task to save the documents.
    """
    def __init__(self, articleset=None, nthreads=4):
        super(ThreadedController, self).__init__(articleset)
        self.nthreads = nthreads

    def _scrape_to_queue(self, scraper, queue):
        """
        Start and join the multithreaded processing of the scraper,
        placing resulting documents on the given queue for saving
        """
        distribute_tasks(tasks=scraper.get_units(), action=scraper.scrape_unit,
                         nthreads=self.nthreads, retry_exceptions=3,
                         output_action=add_to_queue_action(queue))


    def scrape(self, scraper):
        result = []
        qpt = QueueProcessorThread(self.save, name="Storer", output_action=result.append)
        qpt.start()
        self._scrape_to_queue(scraper, qpt.input_queue)
        qpt.input_queue.done=True
        qpt.input_queue.join()
        return result


def scrape_logged(controller, scrapers, deduplicate = False):
    """Use the controller to scrape the given scrapers.

    @return: a tuple (counts, log)
             counts: a mapping of number of articles scraper per scraper
             log: a string representation of the log messages from the scrapers
    """
    result = {s : [] for s in scrapers}
    from sentry.client.handlers import SentryHandler
    amcatlogging.install_handler(SentryHandler())

    counts = dict((s, 0) for s in scrapers)
    log_stream = StringIO()
    with amcatlogging.install_handler(logging.StreamHandler(stream=log_stream)):
        for a in controller.scrape(scrapers, deduplicate=deduplicate):
            counts[a.scraper] += 1
            result[a.scraper].append(a)
                
    return counts, log_stream.getvalue(), result




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest, amcatlogging
from amcat.scraping.scraper import Scraper
from amcat.models.article import Article
from datetime import date

class _TestScraper(Scraper):
    medium_name = 'xxx'
    def __init__(self, project=None,articleset=None, n=10):
        if project is None:
            project = amcattest.create_test_project()
        if articleset is None:
            articleset = amcattest.create_test_set()
        super(_TestScraper, self).__init__(articleset=articleset.id,project=project.id)
        self.n = n

    def _get_units(self):
        return range(self.n)
    def _scrape_unit(self, unit):
        yield Article(headline=str(unit), date=date.today())

class TestController(amcattest.PolicyTestCase):
    def test_scraper(self):
        """Does the simple controller and saving work?"""
        p = amcattest.create_test_project()
        s = amcattest.create_test_set()
        c = SimpleController()
        ts = _TestScraper(project=p,articleset=s)
       
        articles = c.scrape(ts)
        self.assertEqual(p.articles.count(), ts.n)
        self.assertEqual(set(articles), set(p.articles.all()))
        self.assertEqual(s, ts.articleset)

    def test_set(self):
        """Are scraped articles added to the set?"""
        p = amcattest.create_test_project()
        s = amcattest.create_test_set()
        c = SimpleController(s)
        ts = _TestScraper(project=p,articleset=s)
        c.scrape(ts)
        self.assertEqual(p.articles.count(), ts.n)
        self.assertEqual(s.articles.count(), ts.n)

    def test_threaded(self):
        """Does the threaded controller and saving work?"""
        p = amcattest.create_test_project()
        from Queue import Queue
        q = Queue()
        c = ThreadedController()
        ts = _TestScraper(project=p)
        # Multithreaded saving does not work in unit test, so save in-thread
        # See below for a 'production test'
        c._scrape_to_queue(ts, q)
        while not q.empty():
            c.save(q.get())
        self.assertEqual(p.articles.count(), ts.n)

class _ErrorArticle(object):
    def save(self):
        list(Article.objects.raw("This is not valid SQL"))
       
class _ErrorScraper(Scraper):
    medium_name = 'xxx'
    def _get_units(self):
        return [1,2]
    def _scrape_unit(self, unit):
        if unit == 1:
            yield _ErrorArticle()
        else:
            yield Article(headline=str(unit), date=date.today())
       
class TestRobustController(amcattest.PolicyTestCase):
    def test_rollback(self):
        c = RobustController()
        s = amcattest.create_test_set()
        sc = _ErrorScraper(project=s.project.id, articleset = s.id)
        with amcatlogging.disable_logging():
            list(c.scrape(sc))
        self.assertEqual(s.articles.count(), 1)
       
       

def production_test_multithreaded_saving():
    """
    Test whether multithreaded saving works.
    Threaded commit does not work in unit test, code below actually creates
        projects and articles, so run on test database only!
    """
    from amcat.models.project import Project
    import threading
    p = Project.objects.get(pk=2)
    s = amcattest.create_test_set(project=p)
    log.info("Created article set {s.id}".format(**locals()))
    c = ThreadedController(s)
    ts = _TestScraper(projectid=p.id)
    articles = c.scrape(ts)
    assert s.articles.count() == ts.n
    assert articles is not None
    assert set(s.articles.all()) == set(articles)

    log.info("[OK] Production test Multithreaded Saving passed")

def production_test_logged_multithreaded_error():
    """
    Test whether multithreaded saving works.
    Threaded commit does not work in unit test, code below actually creates
        projects and articles, so run on test database only!
    """
    from amcat.models.project import Project
    from amcat.tests.test_scraping import TestDatedScraper, TestErrorScraper
    p = Project.objects.get(pk=2)

    s1 = TestDatedScraper(date = date.today(), project=p.id)
    s2 = TestErrorScraper(date = date.today(), project=p.id)

    counts, log = scrape_logged(ThreadedController(), [s2])

    print("Scraping finished:")
    for c, n in counts.items():
        print("%s : %i" % (c.__class__.__name__, n))
    if log:
        print("\nDetails:\n%s" % log)
    import time;time.sleep(.1)


if __name__ == '__main__':
    #production_test_multithreaded_saving()
    amcatlogging.setup()
    production_test_logged_multithreaded_error()
