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
from amcat.models.project import Project
import logging;log = logging.getLogger(__name__)

class RegisterScraperForm(forms.Form):
    module = forms.CharField()
    class_name = forms.CharField()
    label = forms.CharField()
    username = forms.CharField(required = False)
    password = forms.CharField(required = False)
    run_daily = forms.BooleanField()
    
    articleset = forms.ModelChoiceField(ArticleSet.objects.all(), required = False)
    #either articleset or new set
    new_set_project = forms.ModelChoiceField(Project.objects.all(), required = False)
    new_set_name = forms.CharField(required = False)


class RegisterScraperScript(Script):
    options_form = RegisterScraperForm
    def run(self, _input):

        scraper_options = {
            'articleset' : self.articleset(),
            'module' : self.options['module'],
            'class_name' : self.options['class_name'],
            'label' : self.options['label'],
            'username' : self.options['username'] or None,
            'password' : self.options['password'] or None,
            'run_daily' : self.options['run_daily']}
                
        log.info("new scraper with options {}".format(scraper_options))

        Scraper.objects.create(**scraper_options)

        log.info("done")

    def articleset(self):
        if self.options['articleset']:
            return self.options['articleset']
        elif self.options['new_set_project']:
            name = self.options['new_set_name'] or self.options['label'] + " scraper"
            return ArticleSet.objects.create(name = name,
                                     project = self.options['new_set_project'],
                                     provenance = "",
                                     indexed = False,
                                     index_dirty = False,
                                     needs_deduplication = True)
        else:
            raise ValueError("please provice articleset or new_set_project, new_set_name is optional")
            
        

          
            
    
if __name__ == '__main__':
    from amcat.tools import amcatlogging
    from amcat.scripts.tools import cli
    amcatlogging.info_module(__name__)
    cli.run_cli(RegisterScraperScript)

