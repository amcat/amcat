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
A Scraper is an object that knows how to scrape a certain resource. A scraper
is called by the controller, 
"""

from django import forms

from amcat.scripts.script import Script
from amcat.models.article import Article

from amcat.scripts.tools import cli

class Scraper(Script):
    output_type = Article

    def run(self, input):
        for u in self.get_units():
            for a in self.scrape_unit(u):
                yield a
    
    def get_units(self):
        return [None]

    def scrape_unit(self, unit):
        return []

class DateForm(forms.Form):
    """
    Form for scrapers that operate on a date
    """
    date = forms.DateField()

class DatedScraper(Scraper):
    options_form = DateForm


if __name__ == '__main__':
    cli.run_cli(DatedScraper)


