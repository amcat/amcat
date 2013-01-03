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

import types

from amcat.models.scraper import Scraper

##############
#### MISC ####
##############

def dictionary(func):
    """This decorator converts a generator yielding (key, value) to a dictionary."""
    def _dictionary(*args, **kwargs):
        return dict(tuple(func(*args, **kwargs)))
    return _dictionary

def iterable(func):
    """This decorator converts a generator to a tuple."""
    def _iterable(*args, **kwargs):
        return tuple(func(*args, **kwargs))
    return _iterable

import re
import inspect

def safeloops(func): 
    """This decorator makes sure only the most inner loop has a skipped iteration when an exception occurs"""
    if "instancemethod" in str(type(func)):
        func = func.__func__


    lines = inspect.getsourcelines(func)[0]
    _import = "from amcat.tools.toolkit import log_error\n"
    add = "with log_error():\n"
    new = []

    killtabs = 0
    for c in lines[0]:
        if c == " ":
            killtabs += 1
        else:
            break

    lines = [line[killtabs:] for line in lines]
    

    tabsize = 0
    for c in lines[1]:
        if c == " ":
            tabsize += 1
        else:
            break

    extra_tab_count = 0
    for_loop_tabs = 0
    for line in lines:
        tabs = len(re.search(r"^(\s*)",line).group(1)) / tabsize
        
        if tabs < for_loop_tabs:
            extra_tab_count -= 1
            
        new.append(" " * tabsize * extra_tab_count + line)
        m = re.match(r"^(\s+)for\s[()\w,]+\sin\s[^ :\n]+:\n$",line)
        
        if m:
            extra_tab_count += 1
            new.append(m.group(1) + " " * tabsize * extra_tab_count + _import)
            new.append(m.group(1) + " " * tabsize * extra_tab_count + add)
            for_loop_tabs = tabs

    code = compile("".join(new),'<string>','exec')

    func.__code__ = code

    return func
    


########################
#### SCRAPING TOOLS ####
########################

def todate(date):
  """Convert datetime object to date object. If `date` can't be converted, return
  withouth modifying"""
  return date.date() if hasattr(date, 'date') else date
  
def filter_docs(docs, date):
    """Some websites do not provide an archive, but only 'previous' and 'next' links. By
    iterating over all pages descending, this function only returns the document with the
    correct date. It stoppes after a page older than `date` is detected.

    @type docs: generator of Documents
    @param docs: Documents in descending order

    @type date: datetime.datetime or datetime.date
    @param date: only return `docs` of `date`"""
    date = todate(date)
    for doc in docs:
        if todate(doc.props.date) == date:
            yield art
        elif todate(doc.props.date) < date:
            break

@dictionary
def parse_form(form):
    """Turn a form in to a dictionary, including hidden fields.

    @type form: lxml-html object
    @param form: form to parse"""
    for inp in form.cssselect('input'):
        yield (inp.get('name'), inp.get('value', '').encode('utf-8'))

@iterable
def parse_coord(coord):
    """Newspapers often create clickable articles using divs and styles. For example:
    
    left:331px; top:495px; width:72px; height:86px

    This function returns a tuple containing (left, top, width, height).

    @type coord: str
    @param coord: coordinate to parse"""
    coords = [x.strip() for x in coord.split(';')]
    return map(int, (x.split(':')[1][:-2] for x in coords))

def parse_coords(elements):
    """Uses parse_coord to parse multiple lxml.html elements' style attributes"""
    return [parse_coord(el.get('style')) for el in elements]



########################
#### MANAGING TOOLS ####
########################
def get_scrapers():
    """
    Get all scraper objects in scrapers/*/*.py.

    @return: scraper objects
    @return type: generator
    """
    from amcat.tools.scraping import processors, scrapers

    PROCESSORS = (processors.Scraper,
                  processors.HTTPScraper,
                  processors.CommentScraper,
                  processors.PCMScraper,
                  processors.GoogleScraper)

    def _get_categories(module=scrapers):
        mods = [getattr(module, m) for m in dir(module)]
        return (m for m in mods if type(m) == types.ModuleType)

    def _get_scraper_modules(category):
        return _get_categories(category)

    for cat in _get_categories():
        for mod in _get_scraper_modules(cat):
            members = [getattr(mod, m) for m in dir(mod)]
            for member in (m for m in members if type(m) == type):
                if member not in PROCESSORS and issubclass(member, processors.Scraper):
                    yield member

def get_scraper_model(scraper_class):
    """Return a model for `scraper_class`.

    Raises amcat.models.scraping.Scraper.DoesNotExists when the model isn't found.

    @type scraper_class: class
    @param scraper_class: scraper

    @return amcat.models.scraping.Scraper object"""
    return Scraper.objects.get(class_name=scraper_class.__name__)


def check_article_duplicates(article,overwrite=False):
    """checks if given article has a duplicate within its articleset"""
    
