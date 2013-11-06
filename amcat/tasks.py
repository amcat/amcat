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


from celery import task, group
import time, logging, types
from celery.utils.log import get_task_logger; log = get_task_logger(__name__)
import logging;log.setLevel(logging.INFO)
from lxml import html, etree

from amcat.models.article import Article
from amcat.models.scraper import Scraper
from amcat.scraping.document import Document


#Things that cannot be serialized:
#- Scraper script (unless...)
#- Any Django model
#- lxml.html.HTMLElements

class LockHack(object):
    #awaiting a better solution
    def acquire(self):pass
    def release(self):pass

#to enable older scraper
def html_off(unit):
    """Turns any HTMLElement objects into text to enable serialisation"""
    t = type(unit)
    if t is str:
        unit = unit.strip()
    elif t in (html.HtmlElement, etree._Element):
        unit = html.tostring(unit)
    elif t in (list, tuple, types.GeneratorType):
        unit = map(html_off, unit)
    elif isinstance(unit, Document):
        if hasattr(unit, 'doc') and unit.doc:
            unit.doc = html.tostring(unit.doc)
        unit.typedict = {}
        for k,v in unit.get_props().items():
            unit.typedict[k] = type(v)
            setattr(unit.props, k, html_off(v))
    return (t,unit)

def html_on(unit):
    """Turns strings back to HTMLElements to be parsed"""
    t,unit = unit
    if t in (html.HtmlElement, etree._Element):
        unit = html.fromstring(unit)
    elif t in (list, tuple, types.GeneratorType):
        return map(html_on, unit)
    elif isinstance(unit, Document):
        if hasattr(unit, 'doc') and unit.doc:
            unit.doc = html.fromstring(unit.doc)
        for k,v in unit.get_props().items():
            setattr(unit.props, k, html_on(v))
    return unit

@task()
def run_scraper(scraper):
    scraper._initialize()
    if hasattr(scraper, 'opener') and hasattr(scraper.opener, 'cookiejar'):
        scraper.opener.cookiejar._cookies_lock = LockHack()
    log.info("Running {scraper.__class__.__name__}".format(**locals()))
    tasks = [scrape_unit_save_unit.s(scraper, html_off(unit)) for unit in scraper._get_units()]
    result = group(tasks).delay()
    return (scraper, result)
    
@task()
def scrape_unit_save_unit(scraper, unit):
    unit = html_on(unit)
    log.info("Recieved unit: {unit}".format(**locals()))
    articles = list(scraper._scrape_unit(unit))

    if len(articles) == 0:
        log.warning("scrape_unit returned 0 units")

    articles = [scraper._postprocess_article(article) for article in articles]
    articles = transfer_parents(articles)

    log.info("saving {n} articles".format(n = len(articles)))
    return Article.ordered_save(articles, articleset = scraper.articleset)

#to be removed
def transfer_parents(articles):
    identifiers = dict([((article.text,article.headline), article) for article in articles])
    for article in articles:
        if article.parent:
            #parents could be either Document or Article instances
            if isinstance(article, Document):
                parent_text = article.parent.props.text
                parent_headline = article.parent.props.headline
            elif isinstance(article, Article):
                parent_text = article.parent.text
                parent_headline = article.parent.headline
            article.parent = identifiers[(parent_text, parent_headline)]
    return articles
