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
    scrapers = Scraper.objects.filter(run_daily=True)
    \
    dates = [datetime.date.today() - datetime.timedelta(days=n) for n in range(14)]
    
    for scraper in scrapers:
        print(scraper.n_scraped_articles(from_date=dates[-1], to_date=dates[0]))
        scraper.articles = scraper.n_scraped_articles(from_date=dates[-1], to_date=dates[0])
        print(scraper.articles)

    scraper_table = ObjectTable(rows=list(scrapers), columns=["id", "label" ,"run_daily"])

    def Set(scraper):
        s = scraper.articleset
        if s is None: return ""
        url = reverse(articleset, args=[s.project.id, s.id])
        return "<a href='{url}'>{s}</a>".format(**locals())
    scraper_table.addColumn(Set)

    def getdate(date, scraper):
        return scraper.articles.get(date, 0)
    
    for date in dates:
        scraper_table.addColumn(partial(getdate, date), str(date)[-5:])
    
    scraper_table = table2htmlDjango(scraper_table, safe=True)
    return render(request, 'navigator/scrapers/index.html', locals())
