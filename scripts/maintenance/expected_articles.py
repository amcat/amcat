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

from amcat.models.scraper import Scraper
from amcat.models.article import Article
from django.db.models import Count
from datetime import date,timedelta


def scraper_ranges(scraper):
    returns = [(0,0)] * 7

    articleset_id = scraper.articleset_id
    rows = Article.objects.filter(articlesetarticle__articleset = articleset_id).extra({'date':"date(date)"}).values('date').annotate(created_count=Count('id'))
                         
    for i,rows in enumerate(sort_weekdays(rows)):
        numbers = [row['created_count'] for row in rows]
        third_q = third_quartile(numbers)
        returns[i] = (third_q/1.5,third_q*2)
        

    return returns


def sort_weekdays(rows):
    days = [[] for L in range(7)] #[[]] * 7 provides 7 of the same list, so don't edit
    for row in rows:
        wkday = row['date'].weekday()
        days[wkday].append(row)
        
    return days
        
def third_quartile(numbers):
    numbers = sorted(numbers)
    L = len(numbers)
    if L == 0:
        return 0
    elif L == 1:
        return numbers[0]
    else:
        pointer = int(L*(3.0/4.0))
        return numbers[pointer]

def get_expected_articles():
    d_ranges = {}
    for scraper in Scraper.objects.all():
        d_ranges[scraper] = scraper_ranges(scraper)
    return d_ranges



if __name__ == '__main__':
    from pprint import pprint
    pprint(get_expected_articles())
        

    
        
        
