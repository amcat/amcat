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

from datetime import date,timedelta

from amcat.models.scraper import Scraper
from amcat.models.article import Article
from amcat.models.medium import Medium
from amcat.scripts.script import Script

class UpdateStatisticsScript(Script):
    def run(self, _input=None):
        today = date.today()
        scrapers = Scraper.objects.filter(active=True)
        for scraper in scrapers:
            medium_name = scraper.get_scraper_class().medium_name
            n_scraped = scraper.n_scraped_articles(
                from_date = today - timedelta(days = 70),
                to_date = today,
                medium = Medium.get_or_create(medium_name))
            by_weekday = self.by_weekday(n_scraped)
            averages = {wkday : sum(nums) / (len(nums) or 1) for wkday, nums in by_weekday.items()}
            minima = [avg/1.5 for wkday,avg in averages.items()]
            maxima = [avg*1.5 for wkday,avg in averages.items()]
            scraper.statistics = [(minima[x],maxima[x]) for x in range(7)]
            print("{scraper} -> {scraper.statistics}".format(**locals()))
            scraper.save()
            
    def by_weekday(self, n_scraped):
        weekdaydict = {i : [] for i in range(7)}
        for day, n in n_scraped.items():
            weekdaydict[day.weekday()].append(n)
        return weekdaydict


if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(UpdateStatisticsScript)
        

    
        
        
