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

from amcat.scraping.document import Document, _ARTICLE_PROPS
from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tasks import run_scraper, LockHack
from amcat.tools.api import AmcatAPI

class Controller(object):
    def run(self, scrapers):
        if not hasattr(scrapers, '__iter__'):
            scrapers = [scrapers]
        for scraper, manager in self._scrape(scrapers):
            log.info("{scraper.__class__.__name__} at date {d} returned {n} articles".format(
                    n = manager.n_articles(),
                    d = 'date' in scraper.options.keys() and scraper.options['date'],
                    **locals()))
            
            self._save(scraper, manager)
            yield (scraper, manager.getmodels())

    def _scrape(self, scrapers):
        """
        Run the given scrapers using the control logic of this controller
        @return: a list of tuples: (scraper, [articles]) per scraper"""
        for scraper in scrapers:
            manager = ArticleManager()
            for unit in scraper._get_units():
                manager.add_articles(scraper._scrape_unit(unit))
            yield (scraper, manager)
            
    def _save(self, scraper, manager):
        """Saves the articles"""
        Article.ordered_save(manager.getmodels())

class APIController(Controller):
    """Saves the articles to the API"""
    def _save(self, scraper, manager):
        #TODO: to access the API we need auth data, 
        #this should be provided by run_cli and the views that run controllers.
        #for now, we will use env variables.
        auth = {'host' : os.environ.get('AMCAT_API_HOST'),
                'user' : os.environ.get('AMCAT_API_USER'),
                'password' : os.environ.get('AMCAT_API_PASSWORD')}
        api = AmcatAPI(**auth)
        api.create_articles(
            scraper.articleset.project.id,
            scraper.articleset.id,
            json_data = manager.getdicts())
            
class ThreadedController(Controller):
    def _scrape(self, scrapers):
        #remove thread locks
        for i, scraper in enumerate(scrapers):
            if hasattr(scraper, 'opener'):
                scraper.opener.cookiejar._cookies_lock = LockHack()
        #generate subtask list, extra check on locks
        subtasks = []
        log.info("initializing scrapers...")
        for scraper in scrapers:
            log.debug("checking pickle for {scraper}".format(**locals()))
            try:
                pickle.dumps(scraper)
            except (pickle.PicklingError, TypeError):
                log.warning("Pickling {scraper} failed".format(**locals()))
            else:
                d = 'date' in scraper.options.keys() and scraper.options['date']                
                log.debug("added {scraper.__class__.__name__} for date {d} to subtasks".format(**locals()))
                for x in range(3):
                    try:
                        scraper._initialize()
                    except Exception:
                        pass
                    else:
                        break
                subtasks.append(run_scraper.s(scraper))
                         
        #run all scrapers
        task = group(subtasks)
        result = task.apply_async()
        log.info("Scrapers are now running in celery")

        #harvest result
        for scraper, output in result.iterate():
            if isinstance(output, Exception):
                log.exception("{scraper} failed".format(**locals()))
                continue
            articles = [inner for outer in output for inner in outer] #[[a,b][c,d]] -> [a,b,c,d]
            manager = ArticleManager(articles, scraper = scraper)
            log.info("{scraper.__class__.__name__} returned {n} articles".format(
                    n = manager.n_articles(), **locals()))
            yield (scraper, manager)
                         
class ThreadedAPIController(ThreadedController, APIController):
    """Controller that runs scrapers asynchronously and saves them via the API"""

class ArticleManager(object):
    """class to manage the overly complex output of scrapers
    takes articles of various classes and types, provides convertion and postprocessing
    also handles parent-child relationships"""
    _articles = []

    def __init__(self, articles = [], scraper = None):
        self._articles = self.add_articles(articles, scraper = scraper)

    def __iter__(self):
        for article in self._articles:
            yield article

    def add_articles(self, articles, scraper = None):
        """articles: a list of unprocessed/processed article/document objects"""
        for a in articles:
            if hasattr(a,'props') and hasattr(a.props,'parent'):
                a.parent = a.props.parent
                del a.props.parent #:(            

        parents = [a for a in articles if not(hasattr(a,'parent'))]
        articles = [self._postprocess(p, articles, scraper) for p in parents]
        self._articles.extend(articles)
        return articles

    def getdicts(self):
        """Returns a list of dictionaries that represent articles
        the 'children' attribute is a list of more articles"""
        return self._articles

    def getmodels(self):
        """Returns a list of (unsaved) article models"""
        #line up all dicts
        articles = self._flatten_articles()
        #which dict corresponds to which model?
        convertdict = [(a, Article(**a)) for a in articles.values()]
        toreturn = []
        #point parent attributes at models
        for _dict, model in convertdict:
            if 'parent' in _dict.keys():
                model.parent = articles[_dict['parent']]
            toreturn.append(model)
        return toreturn

    def getjson(self):
        """Returns articles in JSON format"""
        return json.dumps(self._articles)

    def n_articles(self):
        return len(self._flatten_articles().keys())

    def _postprocess(self, article, articles, scraper = None):
        """process one article and it's children"""
        artdict = {'metastring' : {}, 'children' : []}

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

        elif isinstance(article, dict):
            artdict = article

        for child in articles:
            if hasattr(child, 'parent') and child.parent == article:
                artdict['children'].append(self._postprocess(child))

        if scraper:
            artdict['medium'] = Medium.get_or_create(scraper.medium_name)
            artdict['project'] = scraper.options['project']

        return artdict

    def _flatten_articles(self):
        """Returns a dict with articles pointing to their parents, rather than being contained by them"""
        toprocess = self._articles[:]
        toreturn = {}
        i = 0
        while toprocess:
            i += 1
            parent = toprocess.pop(0)
            for child in parent['children']:
                child['parent'] = i
                toprocess.append(child)
            toreturn[i] = parent
        return toreturn
            

###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest, amcatlogging
from amcat.scraping.scraper import Scraper
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
