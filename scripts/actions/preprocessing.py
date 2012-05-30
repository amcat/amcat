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
import random
from django.db import transaction
from django import forms

from amcat.models import ArticleSet 
from amcat.scripts.script import Script
from amcat.nlp.preprocessing import set_preprocessing_actions

import logging; log = logging.getLogger(__name__)

def drawSample(aids, nsample):
    random.shuffle(aids)
    return aids[:nsample]

class PreprocessingAction(Script):
    class options_form(forms.Form):
        sets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.all())
        nsample = forms.IntegerField(required=False)
    
    @transaction.commit_on_success
    def run(self, _input=None):
        for article_set in self.options["sets"]:
            aids = [aid for (aid,) in article_set.articles.values_list("id")]
            if self.options["nsample"]:
                aids = drawSample(aids, self.options["nsample"])
            log.info("Updating preprocessing status for {n} articles in set {article_set}"
                     .format(n=len(aids), **locals()))
            print("ASSIGNING %s ARTICLES FROM ARTICLESET %s (%s)" % (len(aids), article_set.id, article_set))
            set_preprocessing_actions(aids)

if __name__ == '__main__':
    from amcat.scripts.tools.cli import run_cli
    run_cli()




###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestPreprocessingAction(amcattest.PolicyTestCase):
    def test_run(self):
        from amcat.models import AnalysisArticle, AnalysisProject
        
        a1, a2 = [amcattest.create_test_article() for _x in range(2)]
        s = amcattest.create_test_set()
        s.add(a1, a2)

        # running action should do nothing - no preprocessing is activated
        PreprocessingAction(sets=[s.id]).run()
        self.assertEqual(len(AnalysisArticle.objects.filter(article__in=[a1, a2])), 0)

        n = amcattest.create_test_analysis()
        AnalysisProject.objects.create(project=s.project, analysis=n)
        self.assertEqual(len(AnalysisArticle.objects.filter(article__in=[a1, a2])), 0)
        PreprocessingAction(sets=[s.id]).run()
        aas = set((aa.analysis, aa.article) for aa in
                  AnalysisArticle.objects.filter(article__in=[a1, a2]))
        self.assertEqual(aas, set([(n, a1), (n, a2)]))
        
        
