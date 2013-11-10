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

import cPickle as pickle
from celery import group
import logging;log = logging.getLogger(__name__)
import os

from amcat.scraping.document import Document
from amcat.models.article import Article
from amcat.tasks import run_scraper, postprocess, LockHack
from amcat.tools.api import AmcatAPI

class Controller(object):
    def run(self, scrapers):
        if not hasattr(scrapers, '__iter__'):
            scrapers = [scrapers]

        for scraper, articles in self._scrape(scrapers):
            log.info("{scraper.__class__.__name__} at date {d} returned {n} articles".format(
                    n = len(articles),
                    d = 'date' in scraper.options.keys() and scraper.options['date'],
                    **locals()))
            self._save(scraper, articles)
            yield (scraper,articles)

    def _scrape(self, scrapers):
        """
        Run the given scrapers using the control logic of this controller
        @return: a list of tuples: (scraper, [articles]) per scraper"""
        articles = []
        for scraper in scrapers:
            for unit in scraper._get_units():
                if type(unit) == str:
                    unit = unit.decode('utf-8').encode('utf-8')
                elif type(unit) == unicode:
                    unit = unit.encode('utf-8')
                log.info("received unit: {unit}".format(**locals()))
                [articles.append(article) for article in scraper._scrape_unit(unit)]
            articles = Controller.postprocess(articles)
            yield (scraper, articles)

    @classmethod
    def postprocess(cls, articles):
        """takes whatever comes out of _scrape_unit and turns it into a list of article dictionaries"""
        for a in articles:
            if hasattr(a,'props') and hasattr(a.props,'parent'):
                a.parent = a.props.parent
                del a.props.parent

        parents = [a for a in articles if not(hasattr(a,'parent'))]
        return [cls._process(p, articles) for p in parents]


    @classmethod
    def _process(cls, article, articles):
        """process one article and it's children"""
        artdict = {'metastring' : {}, 'children', []}

        if isinstance(article, Document):
            for prop, value in article.getprops().items():
                value = article._convert(value)
                if prop in _ARTICLE_PROPS:
                    artdict[prop] = value
                else:
                    artdict['metastring'][prop] = value

        elif isinstance(article, Article):
            fieldnames = [f.name for f in model._meta.fields]
            for prop in fieldnames:
                if hasattr(article, prop):
                    artdict[prop] = getattr(article, prop)

        for child in articles:
            if child.parent = article:
                artdict['children'].append(cls._process(child))

        return artdict

    def _save(self, scraper, articles):
        """This controller's implementation of saving articles. Defaults to saving to the API"""
        #TODO: to access the API we need auth data, 
        #this should be provided by run_cli and the views that run controllers.
        #for now, we will use env variables.
        auth = {'host' : os.environ.get('AMCAT_API_HOST'),
                'user' : os.environ.get('AMCAT_API_USER'),
                'password' : os.environ.get('AMCAT_API_PASSWORD')}

        api = AmcatAPI(*auth)
        api.create_articles(scraper.project, scraper.articleset, json_data = json.dumps(articles))
            
class ThreadedController(Controller):
    def _scrape(self, scrapers):
        #remove thread locks
        for i, scraper in enumerate(scrapers):
            if hasattr(scraper, 'opener'):
                scraper.opener.cookiejar._cookies_lock = LockHack()
                
        #generate subtask list, extra check on locks
        subtasks = []
        for scraper in scrapers:
            log.debug("checking pickle for {scraper}".format(**locals()))
            try:
                pickle.dumps(scraper)
            except (pickle.PicklingError, TypeError):
                log.exception("Picking {scraper} failed".format(**locals()))
            else:
                d = 'date' in scraper.options.keys() and scraper.options['date']
                log.info("added {scraper.__class__.__name__} for date {d} to subtasks".format(**locals()))
                subtasks.append(run_scraper.s(scraper))
                         
        #run all scrapers
        task = group(subtasks)
        result = task.apply_async()

        #harvest result, run processing task for each set of articles, yield
        for scraper, articles in result.iterate():
            articles = [inner for outer in articles for inner in outer] #[[a,b][c,d]] -> [a,b,c,d]
            articles = ~postprocess.s(articles)
            yield (scraper,articles)
                         
                   

      
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest, amcatlogging
from amcat.scraping.scraper import Scraper
from amcat.models.article import Article
from datetime import date

class _TestScraper(Scraper):
    medium_name = 'xxx'
    def __init__(self, project = None, articleset = None):
        if project is None:
            project = amcattest.create_test_project()
        if articleset is None:
            articleset = amcattest.create_test_set()
        super(_TestScraper, self).__init__(articleset = articleset.id, project = project.id)

    def _get_units(self):
        for unit in [
            u'\u03B1\u03B2\u03B3',
            Article(headline = u'\u03B4', date = date.today()),
            1337]:
            yield unit

    def _scrape_unit(self, unit):
        unit = unicode(str(unit), 'utf-8')
        parent = Article(headline = unit, date = date.today())
        child = Article(headline = "re: " + unit, date = date.today(), parent = parent)
        yield child
        yield parent
                         
class TestControllers(amcattest.PolicyTestCase):

    def test_scraper(self, c = Controller()):
        """Does the controller run the scrapers correctly?"""
        ts1 = _TestScraper()
        ts2 = _TestScraper()
        out = list(c.run([ts1,ts2]))
        articles = [articles for scraper, articles in out] #[(a,b),(c,d)] -> [b,d]
        articles = [inner for outer in articles for inner in outer] #[[a,b][c,d]] -> [a,b,c,d]

        self.assertEqual(len(out), 2)
        self.assertEqual(len(articles), 6)
                         
    def test_save(self, c = Controller()):
        """Does the controller save the articles to the set and project?"""
        p = amcattest.create_test_project()
        s = amcattest.create_test_set()
        result = list(c.run(_TestScraper(project = p)))
        self.assertEqual(len(result), p.articles.count())
        self.assertEqual(len(result), s.articles.count())

    """def test_threaded(self):
        self.test_scraper(c = ThreadedController())
        self.test_save(c = ThreadedController())"""
