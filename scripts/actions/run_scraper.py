#!/usr/bin/python
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
Script run a scraper from the DB
"""

import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.models.scraper import Scraper
from amcat.scraping.scraper import DBScraperForm
from amcat.scraping.controller import RobustController

class RunScraperForm(forms.Form):
    scraper = forms.ModelChoiceField(queryset=Scraper.objects.all())
    date = forms.CharField()

class AddProject(Script):
    """Add a project to the database."""

    options_form = RunScraperForm
    output_type = None

    def run(self, _input=None):
        scraper = self.options["scraper"].get_scraper(date=self.options["date"])
        controller = RobustController()
        controller.scrape(scraper)

if __name__ == '__main__':
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.scraping.controller")
    from amcat.scripts.tools import cli
    cli.run_cli()
