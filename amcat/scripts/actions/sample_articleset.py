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

class SampleSet(Script):
    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        sample = forms.CharField(help_text="Sample in absolute number or percentage")
        target_articleset_name = forms.CharField(help_text="Name for the new article set")

        def clean_sample(self):
            sample = self.cleaned_data["sample"]
            try:
                if sample.endswith("%"):
                    result = float(sample[:-1]) / 100
                else:
                    result = int(sample)
            except ValueError:
                raise forms.ValidationError("The sample should be a whole number or percentage, not {sample!r}".format(**locals()))
            self.cleaned_data["sample"] = result
            return result
            
    def _run(self, articleset, sample, target_articleset_name):
        log.info("Sampling {sample} from {articleset}".format(**locals()))
        if not isinstance(sample, int):
            n = articleset.articles.count()
            sample = int(round(n * sample))
            log.info("Sampling {sample} of {n} articles".format(**locals()))

            
        selected = articleset.articles.order_by('?')[:sample]
        ids = [x for (x,) in selected.values_list("pk")]
            
        target_set = ArticleSet.objects.create(name=target_articleset_name, project=articleset.project)
        log.info("Created set {target_set.id}:{target_set} in project {target_set.project_id}:{target_set.project}!".format(**locals()))
        
        target_set.add_articles(ids)

        log.info("Done!")
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()

