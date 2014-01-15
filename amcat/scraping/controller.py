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

import cPickle as pickle
from celery import group
import logging;log = logging.getLogger(__name__)
import os
from collections import namedtuple

from amcat.scraping.document import Document, _ARTICLE_PROPS
from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.tasks import _scrape_task, _scrape_unit_task, LockHack, convert
from amcat.tools.api import AmcatAPI

ScrapeError = namedtuple("ScrapeError", ["i", "unit", "error"])

class Controller(object):
    def __init__(self):
        self.errors = []

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
        @return: a list of tuples: (scraper, manager) per scraper"""
        for scraper in scrapers:
            scraper._initialize()
            manager = ArticleManager()
            try:
                units = list(scraper._get_units())
            except Exception as e:
                self.errors.append(ScrapeError(None,None,e))
                log.exception("scraper._get_units failed")
                continue
            
            for i, unit in enumerate(units):
                try:
                    articles = list(scraper._scrape_unit(unit))
                except Exception as e:
                    log.exception("scraper._scrape_unit failed")
                    self.errors.append(ScrapeError(i,unit,e))
                    continue
                try:
                    manager.add_articles(articles, scraper = scraper)                    
                except Exception as e:
                    self.errors.append(ScrapeError(i,unit,e))
                    log.exception("processing articles failed")
            yield scraper, manager
            
    def _save(self, scraper, manager):
        """Saves the articles"""
        articles, errors = Article.ordered_save(manager.getmodels(), scraper.options['articleset'])
        for e in errors:
            self.errors.append(ScrapeError(None,None,e))


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
    def run(self, scrapers):
        """_scrape and _scrape_unit are called from subtasks"""
        if not hasattr(scrapers, '__iter__'):
            scrapers = [scrapers]
        for scraper in self._preparescrapers(scrapers):
            # Calls _scrape
            log.info("Starting {scraper.__class__.__name__}".format(**locals()))
            _scrape_task.apply_async((self, scraper))

    def _scrape(self, scraper):
        scraper._initialize()
        log.info("Running {scraper.__class__.__name__}".format(**locals()))

        try:
            tasks = [_scrape_unit_task.s(self, scraper, convert(unit)) for unit in scraper._get_units()]
        except Exception as e:
            log.exception("get_units for {scraper.__class__.__name__} failed".format(**locals()))
        else:
            # Calls _scrape_unit for each unit
            group(tasks).delay()

    def _scrape_unit(self, scraper, unit):
        log.info("Recieved {unit} from {scraper}".format(**locals()))
        try:
            articles = list(scraper._scrape_unit(unit))
        except Exception:
            log.exception("_scrape_unit failed")
        manager = ArticleManager(articles, scraper)
        self._save(scraper, manager)

    def _preparescrapers(self, scrapers):
        """
        Remove common lock,
        Check for serializability,
        Remove bound_form (memory issue, contains whole articlesets)
        """
        for scraper in scrapers:
            scraper.bound_form = None
            if hasattr(scraper, 'opener'):
                scraper.opener.cookiejar._cookies_lock = LockHack()
            try:
                pickle.dumps(scraper)
            except (pickle.PicklingError, TypeError):
                log.exception("Pickling {scraper} failed".format(**locals()))
            else:
                yield scraper

                         
class ThreadedAPIController(ThreadedController, APIController):
    """Controller that runs scrapers asynchronously and saves them via the API"""


class ArticleManager(object):
    """class to manage the overly complex output of scrapers
    takes articles of various classes and types, provides convertion and postprocessing
    also handles parent-child relationships"""

    def __init__(self, articles = [], scraper = None):
        self._articles = []
        self.add_articles(articles, scraper = scraper)

    def __iter__(self):
        for article in _articles:
            yield article

    def add_articles(self, articles, scraper = None):
        """articles: a list of unprocessed/processed article/document objects"""
        articles = list(articles)
        for a in articles:
            if hasattr(a,'props') and hasattr(a.props,'parent'):
                a.parent = a.props.parent
                del a.props.parent #:(            

        parents = [a for a in articles if not(hasattr(a,'parent')) or a.parent not in articles]
        articles = [self._postprocess(p, articles, scraper) for p in parents]
        self._articles.extend(articles)

    def getdicts(self):
        """Returns a list of dictionaries that represent articles
        the 'children' attribute is a list of more articles"""
        return self._articles

    def getmodels(self):
        """Returns a list of (unsaved) article models"""
        #line up all dicts
        articles = self._flatten_articles()
        #which dict corresponds to which model?
        convertdict = []
        for a in articles.values():
            props = dict(**a)
            if 'parent' in props.keys():
                del props['parent']
            convertdict.append((a, Article(**props)))
        toreturn = []
        #point parent attributes at models
        for _dict, model in convertdict:
            if 'parent' in _dict.keys() and _dict['parent']:
                parentdict = articles[_dict['parent']]
                for _dict2, model2 in convertdict:
                    if parentdict == _dict2:
                        model.parent = model2
            toreturn.append(model)
        return toreturn

    def getjson(self):
        """Returns articles in JSON format"""
        return json.dumps(self._articles)

    def n_articles(self):
        """Amount of articles including children"""
        return len(self._flatten_articles().keys())

    def _postprocess(self, article, articles, scraper):
        """process one article and it's children"""
        artdict = self._make_dict(article)

        #handle children
        for child in articles:            
            if self._isparent(article, child):
                if isinstance(child, dict):
                    del child['parent']
                artdict['children'].append(self._postprocess(child, articles, scraper))

        #scraper data to fill in blanks
        if scraper:
            if not 'medium' in artdict.keys():
                if self._iscomment(article):
                    artdict['medium'] = Medium.get_or_create(scraper.medium_name + " - Comments")
                else:
                    artdict['medium'] = Medium.get_or_create(scraper.medium_name)
            if not 'project' in artdict.keys():
                artdict['project'] = scraper.options['project']

        return artdict

    def _iscomment(self, article):
        """Is this article marked as a comment?"""
        if hasattr(article, 'is_comment') and article.is_comment:
            return True
        elif isinstance(article, dict) and 'is_comment' in article.keys() and article['is_comment']:
            return True
        else: return False

    def _isparent(self, article, child):
        """Is this object a parent of this model/Document/dict?"""
        if hasattr(child, 'parent') and child.parent == article:
            return True
        elif isinstance(child, dict) and 'parent' in child.keys() and child['parent'] == article:
            return True
        else: return False

    def _make_dict(self, article):
        """called by _postprocess, converts any type of article into a dict"""
        artdict = {'metastring' : {}, 'children' : []}
        if isinstance(article, Document):
            for prop, value in article.getprops().items():
                value = article._convert(value)
                if prop in _ARTICLE_PROPS:
                    artdict[prop] = value
                else:
                    artdict['metastring'][prop] = value
        elif isinstance(article, Article):
            fieldnames = [f.name for f in article._meta.fields]
            for prop in fieldnames:
                if hasattr(article, prop):
                    artdict[prop] = getattr(article, prop)
        elif isinstance(article, dict):
            artdict = article
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
        if unit == 1337:
            a = 1 / 0 #test error handling
        unit = unicode(str(unit), 'utf-8')
        parent = Article(headline = unit, date = date.today())
        child = Article(headline = "re: " + unit, date = date.today(), parent = parent)
        yield child
        yield parent
        #total unit count: 4

class TestController:#(amcattest.AmCATTestCase):
    controllers = [Controller(), ThreadedAPIController()]
    
    @amcattest.use_elastic
    def test_run(self):
        """Test whether controller runs without error, and whether it still does using the API and multithreaded"""
        for c in self.controllers:
            s = _TestScraper()
            c.run(s)

    @amcattest.use_elastic
    def test_save(self):
        """Test whether articles get saved in the set and project"""
        for c in self.controllers:
            p = amcattest.create_test_project()
            a_s = amcattest.create_test_set(project = p)
            s = _TestScraper(project = p, articleset = a_s)
            g = c.run(s)
            if g: #sometimes a generator
                list(g) 
            self.assertEqual(p.articles.count(), 4)
            self.assertEqual(a_s.articles.count(), 4)

    @amcattest.use_elastic
    def test_parenting(self):
        """Are parent articles nurturing their children well?"""
        for c in self.controllers:
            p = amcattest.create_test_project()
            s = _TestScraper(project = p)
            r = c.run(s)
            if r: #sometimes a generator
                list(r) 
            self.assertTrue(any([hasattr(a, 'parent') for a in p.articles.all()]))
            
if __name__ == "__main__":
    import unittest
    unittest.main()

