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
Script to check and progress parsing results
"""

import logging; log = logging.getLogger(__name__)

from django import forms
from django.db import transaction

from amcat.models import AnalysedArticle, Plugin, ArticleSet
from amcat.scripts.script import Script

PLUGINTYPE_PARSER=1

class CheckParsing(Script):
    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all(), required=False)
        analysed_articles = forms.ModelMultipleChoiceField(queryset=AnalysedArticle.objects.all(), required=False)
        check_only = forms.BooleanField(initial=False, required=False)
        plugin = forms.ModelChoiceField(queryset=Plugin.objects.filter(plugin_type__id=1), required=False)
        
    def _run(self, articleset=None, analysed_articles=None, check_only=False, plugin=None):
        if not analysed_articles:
            if articleset:
                analysed_articles = (AnalysedArticle.objects.filter(done=False, error=False, article__articlesets_set=articleset.id)
                                     .select_related("plugin"))
                
            else:
                # select all (!)
                analysed_articles = AnalysedArticle.objects.filter(done=False, error=False).select_related("plugin")
            if plugin:
                analysed_articles = analysed_articles.filter(plugin=plugin)
        self.process(analysed_articles)
                
    def process(self, articles):
        for aa in articles:
            parser = aa.plugin.get_class()()
            try:
                msg = None
                if self.options["check_only"]:
                    result = parser.check_article(aa)
                else:
                    result = parser.retrieve_article(aa)
            except Exception, e:
                result = "Error"
                msg = repr(e)
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()

