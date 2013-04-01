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
Script to get queries for a codebook
"""

import logging; log = logging.getLogger(__name__)

from django import forms
from django.db import transaction

from amcat.scripts.script import Script
from amcat.models import ArticleSet, Plugin, AnalysedArticle

PLUGINTYPE_PARSER=1

class AssignParsing(Script):
    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        plugin = forms.ModelChoiceField(queryset=Plugin.objects.filter(plugin_type__id=PLUGINTYPE_PARSER))
        resubmit_error = forms.BooleanField(initial=False, required=False)
                                        
    def _run(self, articleset, plugin, resubmit_error):
        if resubmit_error:
            to_parse = list(AnalysedArticle.objects.filter(plugin=plugin, error=True, article__articlesets_set=articleset))
        else:
            to_parse = list(articleset.articles.exclude(analysedarticle__plugin_id=plugin).only("id"))
        log.info("(Re-)Assigning {n} articles from set {articleset.id} to be parsed by plugin {plugin.id}"
                 .format(n=len(to_parse), **locals()))
        if to_parse:
            parser = plugin.get_class()()
            for article in to_parse:
                with transaction.commit_on_success():
                    parser.submit_article(article)
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()

