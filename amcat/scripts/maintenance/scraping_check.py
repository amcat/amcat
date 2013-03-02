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
Script to be run daily after daily.py, checking it's success and reporting to admins in case of failure (via mail)
"""

from amcat.models.scraper import Scraper
from amcat.models.article import Article
from amcat.scripts.script import Script
from amcat.tools import toolkit, sendmail

import logging;log = logging.getLogger(__name__)
import os
from django import forms
from datetime import date

MAIL_HTML = """<h3>Report for daily scraping on {datestr}</h3>

<p>The following scrapers were run:</p>
{table}

<p>For log details, ssh to amcat-dev.labs.vu.nl, then open /home/amcat/log/daily_{_date.year:04d}-{_date.month:02d}-{_date.day:02d}.txt</p>

<p>For a complete overview of last week's results, navigate to http://amcat-production.labs.vu.nl/navigator/scrapers</p>
"""

MAIL_ASCII = MAIL_HTML
for tag in ['h3','p']:
    MAIL_ASCII = unicode(MAIL_ASCII.replace("<{}>".format(tag), "").replace("</{}>".format(tag), ""))
    
class ScrapingCheckForm(forms.Form):
    date = forms.DateField()
    mail_to = forms.CharField()

class ScrapingCheck(Script):
    options_form = ScrapingCheckForm

    def run(self, _input):
        log.info("starting.. getting data")
        result = self.get_result()
        self.send_mail(result)

    def make_table(self, result):
        from amcat.tools.table.table3 import DictTable

        table = DictTable()

        for r in result:
            if r['expected'] == "unknown":
                exvalue = "unknown"
            else:
                exvalue = "{0:.2f}-{1:.2f}".format(r['expected'][0], r['expected'][1])
            table.addValue(
                row = r['scraper'],
                col = "expected range",
                value = exvalue
                )
            table.addValue(
                row = r['scraper'],
                col = "total scraped",
                value = r['count']
                )
            table.addValue(
                row = r['scraper'],
                col = "successful",
                value = r['success']
                )
        return table

    def send_mail(self, result):
        
        table = self.make_table(result).output(rownames = True)
    
        n = sum([r['count'] for r in result])
        succesful = sum([r['success'] for r in result])
        total = len(result)

        datestr = toolkit.writeDate(self.options['date'])

        subject = "Daily scraping for {datestr}: {n} articles, {succesful} out of {total} scrapers succesful".format(**locals())
    
        _date = self.options['date']
        content = MAIL_ASCII.format(**locals())
        for addr in self.options['mail_to'].split(","):
            sendmail.sendmail("toon.alfrink@gmail.com",
                     addr, subject, None, content)



    def get_result(self):
        result = []
        for scraper in Scraper.objects.all():
            if scraper.statistics:
                n_expected = scraper.statistics[self.options['date'].weekday()]
            else:
                n_expected = "unknown"
            n_scraped = Article.objects.filter(
                articlesetarticle__articleset = scraper.articleset.id,
                date__contains = self.options['date']
                ).count()

            if n_expected == "unknown":
                if n_scraped > 0:
                    success = True
                else:
                    success = False
            else:
                if n_scraped < n_expected[0]:
                    success = False
                else:
                    success = True

            scraper_result = {
                'scraper':scraper,
                'count':n_scraped,
                'expected':n_expected,
                'success':success
                }
                
            log.info("""
scraper: {scraper}
\tcount: {count}
\texpected: {expected}
\tsuccess?: {success}
""".format(**scraper_result))
                    
            result.append(scraper_result)

        return result


if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(ScrapingCheck)
