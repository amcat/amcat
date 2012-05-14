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
Script that updates the preprocessing status of a given article set
"""
from django.db import transaction
from django import forms

from amcat.models import ArticleSet 
from amcat.scripts.script import Script
from amcat.nlp.preprocessing import set_preprocessing_actions

import logging; log = logging.getLogger(__name__)

class PreprocessingDaemon(Script):

    class options_form(forms.Form):
        sets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.all())
    
    @transaction.commit_on_success
    def run(self, _input=None):
        for article_set in self.options["sets"]:
            aids = [aid for (aid,) in article_set.articles.values_list("id")]
            log.info("Updating preprocessing status for {n} articles in set {article_set}"
                     .format(n=len(aids), **locals()))
            set_preprocessing_actions(aids)

if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli()
