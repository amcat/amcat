#!/usr/bin/python

##########################################################################
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


import logging; log = logging.getLogger(__name__)

from django import forms
from django.db import transaction

from amcat.scripts.script import Script
from amcat.models import ArticleSet, Article

from amcat.nlp import sbd

class SplitArticles(Script):
    """
    Perform a keyword query on an articleset.
    """
    class options_form(forms.Form):
        articlesets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.all())

    @transaction.commit_on_success    
    def run(self, _input=None):
        sets = self.options['articlesets']
        to_split = list(Article.objects.filter(articlesets__in=sets, sentences=None))
        n = len(to_split)

        log.info("Will split {n} articles".format(**locals()))
        for i, article in enumerate(to_split):
            if not i % 100:
                log.info("Splitting article {i}/{n}".format(**locals()))

            sbd.create_sentences(article)

        log.info("Splitted {n} articles!".format(**locals()))
        
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
        
