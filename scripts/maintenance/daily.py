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
Script to be run daily for data input (scraping, preprocessing etc.
"""

from datetime import date, timedelta

import logging;
from amcat.scraping.controller import RobustController

log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script

from amcat.scraping.controller import scrape_logged
from amcat.models.scraper import get_scrapers

from amcat.tools import toolkit, sendmail

from amcat.tools.table.table3 import ListTable
from amcat.tools.table.tableoutput import table2html

MAIL_HTML = """<h3>Report for daily scraping on {datestr}</h3>

<p>The following scrapers were run:</p>
{table}

<h3>Log Details</h3>
<pre>
{messages}
</pre>"""


MAIL_ASCII = MAIL_HTML
for tag in ["h3", "p", "pre"]:
    MAIL_ASCII = MAIL_ASCII.replace("<%s>"%tag, "").replace("</%s>"%tag, "")

EMAIL = "amcat-scraping@googlegroups.com"

def send_email(count, messages, date):
    days = []; firstdate = date - timedelta(days=7)
    while date >= firstdate:
        days.append(date)
        date -= timedelta(days=1)


    tabledata = []

    for (s,n) in count.items():
        for r in tabledata:
            if s.__class__.__name__ == r[0]:
                for i in range(len(days)):
                    if s.options['date'] == days[i]:
                        r[i+1] = n
            else:
                row = [s.__class__.__name__]
                for i in range(len(days)):
                    if s.options['date'] == days[i]:
                        row[i+1] = n
                tabledata.append(row)
                        

    n = sum(count.values())
    tabledata.append(("Total", n))
    t = ListTable(tabledata, colnames=["Scraper"]+days)
    tabledata_ascii = t.output(useunicode=False, box=False)
    tabledata_html = table2html(t, printRowNames=False)
    succesful = len([1 for (s,n2) in count.items() if n2>0])
    total = len(count.items())

    datestr = toolkit.writeDate(date.today())

    mail_ascii = MAIL_ASCII.format(table=tabledata_ascii, **locals())
    mail_html = MAIL_HTML.format(table=tabledata_html, **locals())

    subject = "Daily scraping for {datestr}: {n} articles, {succesful} out of {total} scrapers succesful".format(**locals())
    
    sendmail.sendmail("toon.alfrink@gmail.com", "toon.alfrink@gmail.com", subject, mail_html, mail_ascii)

    

class DailyForm(forms.Form):
    date = forms.DateField()

class DailyScript(Script):
    options_form = DailyForm

    def run(self, _input):
        date = self.options['date']

        scrapers = list(get_scrapers(date=date))

        log.info("Starting scraping with {} scrapers: {}".format(
                len(scrapers), [s.__class__.__name__ for s in scrapers]))
        count, messages =  scrape_logged(RobustController(), scrapers)
        
        log.info("Sending email...")
        
        send_email(count, messages, date)

        log.info("Done")
        
if __name__ == '__main__':
    from amcat.tools import amcatlogging
    from amcat.scripts.tools import cli
    amcatlogging.info_module("amcat.scraping.scraper")
    amcatlogging.debug_module("amcat.scraping.controller")        
    cli.run_cli(DailyScript)
