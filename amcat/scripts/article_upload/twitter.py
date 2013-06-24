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
Simple scraping of twitter API
"""

from django import forms
from amcat.scraping.scraper import ScraperForm, Scraper
from amcat.models import Article

class Twitter(Scraper):
    medium_name = "twitter"
    
    class options_form(ScraperForm):
        key = forms.CharField(required=True, help_text='Twitter API key')
        keyword = forms.CharField(required=True, help_text='Keyword to search')

        def clean_articleset_name(self):
            """If article set name not specified, use keyword instead"""
            if self.data.get('keyword') and not (self.cleaned_data.get('articleset_name') or self.cleaned_data.get('articleset')):
                return self.data.get('keyword')
            else:
                return ScraperForm.clean_articleset_name(self)
        
    def _initialize(self):
        key = self.options['key']
        print "Connecting to twitter with key", key

    def _get_units(self):
        keyword = self.options['keyword']
        print "Searching twitter on keyword", keyword
        return ["bla", "ble", "blo"]

    def _scrape_unit(self, unit):
        yield Article(text=unit, headline=unit, date='2010-01-01')

