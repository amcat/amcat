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
Script to get analysis_articles and mark them started=True
"""

import logging; log = logging.getLogger(__name__)

from django import forms
from django.db import transaction

from amcat.scripts.script import Script
from amcat.models import Analysis, AnalysisArticle

class GetAnalysisArticles(Script):
    """Add a project to the database."""

    output_type = None
    class options_form(forms.Form):
        analysis = forms.ModelChoiceField(queryset=Analysis.objects.all())
        narticles = forms.IntegerField(required=False, initial=10)

    def run(self, _input=None):
        analysis, n = (self.options[x] for x in ['analysis', 'narticles'])
        log.info("Getting {n} articles from analysis {analysis}".format(**locals()))
        return [dict(id=aa.id, article_id=aa.article_id)
                for aa in get_articles(analysis, n)]

@transaction.commit_on_success
def get_articles(analysis, n):
    """Get n articles to do for this analysis, setting them started=True"""

    # in django 1.4 this can be done using select_for_update()...
    result = (AnalysisArticle.objects
              .filter(analysis=analysis, started=False, done=False, delete=False)
              .only("id", 'article')[:10])
    sql = str(result.query) +" FOR UPDATE"
    result = list(AnalysisArticle.objects.raw(sql))

    if result:
        AnalysisArticle.objects.filter(id__in=[a.id for a in result]).update(started=True)

    return result

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    print cli.run_cli()


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestGetAnalysisArticles(amcattest.PolicyTestCase):

    def test_get_articles(self):
        """Will fail on sqlite!"""
        analysis = amcattest.create_test_analysis()
        arts = [amcattest.create_test_analysis_article(analysis=analysis) for x in range(10)]
        x = list(get_articles(analysis, 7))
        self.assertEqual(len(x), 7)
        x = list(get_articles(analysis, 7))
        self.assertEqual(len(x), 3)
        x = list(get_articles(analysis, 7))
        self.assertEqual(len(x), 0)
