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

from django.shortcuts import render
from django.core.urlresolvers import reverse
from navigator.utils.auth import check
from navigator.views.project import articleset
import logging; log = logging.getLogger(__name__)
import datetime
from functools import partial

from amcat.models.scraper import Scraper

from amcat.tools.table.table3 import ObjectTable
from amcat.tools.table.tableoutput import table2htmlDjango

def index(request):
    daily_scrapers = list(Scraper.objects.filter(run_daily=True,active=True))
    non_daily_scrapers = list(Scraper.objects.filter(run_daily=False,active=True))
    inactive_scrapers = list(Scraper.objects.filter(active=False))
    dates = [datetime.date.today() - datetime.timedelta(days=n) for n in range(14)]

    scraper_lists = {"daily_table":daily_scrapers,
                     "non_daily_table":non_daily_scrapers,
                     "inactive_table":inactive_scrapers}

    for s_list in scraper_lists.values():
        for scraper in s_list:
            scraper.articles = scraper.n_scraped_articles(from_date=dates[-1], to_date=dates[0])

    scraper_tables = {name : ObjectTable(rows=s_list, columns=["id", "label"]) for name,s_list in scraper_lists.items()}

    def Set(scraper):
        s = scraper.articleset
        if s is None: return ""
        url = reverse(articleset, args=[s.project.id, s.id])
        return "<a href='{url}'>{s}</a>".format(**locals())

    for s_table in scraper_tables.values():
        s_table.addColumn(Set)

    def getdate(date, scraper):
        return scraper.articles.get(date, 0)
    
    for date in dates:
        for s_table in scraper_tables.values():
            s_table.addColumn(partial(getdate, date), str(date)[-5:])

    table_dict = {}
    for t_name, s_table in scraper_tables.items():
        table_dict[t_name] = table2htmlDjango(s_table, safe=True)

    return render(request, 'navigator/scrapers/index.html', dict(locals().items() + table_dict.items()))
