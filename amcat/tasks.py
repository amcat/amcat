from __future__ import absolute_import
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


from .amcatcelery import app
import time, logging, types
from celery.utils.log import get_task_logger; log = get_task_logger(__name__)
import logging;log.setLevel(logging.INFO)
from lxml import html, etree
from html2text import html2text

from amcat.models.article import Article
from amcat.models.scraper import Scraper
from amcat.scraping.document import Document


#Things that cannot be serialized:
#- Scraper script (unless...)
#- Any Django model
#- lxml.html.HTMLElements

#since html elements are not serializable, we will convert them early
def convert(unit):
    t = type(unit)
    if isinstance(unit, Document):
        for prop, value in unit.getprops().items():
            value = convert(value)
            setattr(unit.props, prop, value)
    elif t in (html.HtmlElement, etree._Element):
        for js in unit.cssselect("script"):
            js.drop_tree()
        unit = html2text(html.tostring(unit)).strip() 
    elif t in (list, tuple, types.GeneratorType):
        unit = tuple(unit)
        if all([type(e) in (html.HtmlElement, etree._Element) for e in unit]):
            unit = "\n\n".join(map(convert, unit))
    return unit

class LockHack(object):
    #awaiting a better solution
    def acquire(self):pass
    def release(self):pass


@app.task
def _scrape_task(controller, scraper):
    controller._scrape(scraper)
    
@app.task
def _scrape_unit_task(controller, scraper, unit):
    controller._scrape_unit(scraper, unit)
