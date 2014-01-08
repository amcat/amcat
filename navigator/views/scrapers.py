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
import logging; log = logging.getLogger(__name__)
import datetime
from functools import partial

from amcat.models.scraper import Scraper
from api.webscripts.show_aggregation import ShowAggregation
from django.http import QueryDict
import json

def index(request):

    scrapers = list(Scraper.objects.filter(run_daily=True,active=True))
    sets = [s.articleset.id for s in scrapers]
    start_date = datetime.date(2014, 01, 01)
    start_date = start_date.strftime("%d-%m-%Y")
    data = {u'yAxis': [u'medium'], u'xAxis': [u'date'],u'dateInterval': [u'day'],
            u'outputType': [u'table'],
            u'datetype': [u'after'],  u'multiselect_id_datetype': [u'after'], u'start_date': [start_date],
            u'projects': [u'1'], u'articlesets': sets, u'multiselect_id_articlesets': sets,
            u'counterType': [u'numberOfArticles'], u'output': [u'html'],
            }

    script = ShowAggregation(1, request.user, data)
    output = script.run().content
    #output = json.loads(output.content)['html']

    print output
    
    return render(request, 'navigator/scrapers/index.html',locals())
