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
Register a scraper from the command line interface
"""

from django import forms

from amcat.scripts.script import Script
from amcat.models.articleset import ArticleSet
from amcat.models.scraper import Scraper
import logging;log = logging.getLogger(__name__)

class RegisterScraperForm(forms.Form):
    module = forms.CharField()
    class_name = forms.CharField()
    label = forms.CharField(required = False)
    articleset = forms.ModelChoiceField(ArticleSet.objects.all())
    username = forms.CharField(required = False)
    password = forms.CharField(required = False)
    run_daily = forms.BooleanField()

class RegisterScraperScript(Script):
    options_form = RegisterScraperForm
    def run(self, _input):
        options = {
            'module' : self.options['module'],
            'class_name' : self.options['class_name'],
            'label' : self.options['label'],
            'username' : self.options['username'],
            'password' : self.options['password'],
            'run_daily' : self.options['run_daily'],
            'articleset' : self.options['articleset']
            }
        
        log.info("new scraper with options {}".format(options))

        new = Scraper(**options)
        new.save()

        log.info("done")
        
    
    
if __name__ == '__main__':
    from amcat.tools import amcatlogging
    from amcat.scripts.tools import cli
    amcatlogging.info_module(__name__)
    cli.run_cli(RegisterScraperScript)

