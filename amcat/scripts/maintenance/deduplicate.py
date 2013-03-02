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


from django import forms
from django.db.models import Min, Max

from amcat.scripts.script import Script
from amcat.scripts.tools import cli

from amcat.models.article import Article
from amcat.models.scraper import Scraper
from amcat.models.articleset import ArticleSet, ArticleSetArticle
from amcat.models.project import Project
import logging; log = logging.getLogger(__name__)
from amcat.tools import amcatlogging
from datetime import timedelta

class DeduplicateForm(forms.Form):
    first_date = forms.DateField(required = False)
    last_date = forms.DateField(required = False)    
    articleset = forms.ModelChoiceField(queryset = ArticleSet.objects.all())
    recycle_bin_project = forms.ModelChoiceField(queryset = Project.objects.all())
    
class DeduplicateScript(Script):
    options_form = DeduplicateForm

    def run(self, _input):
        mode = self.handle_input()
        if mode == "date range":
            self.options['date'] = self.options['first_date']
            self.run_range(_input)

        elif mode == "single date":
            self.options['date'] = self.options['first_date']
            self._run(_input)

        elif mode == "whole set":
            articles = Article.objects.filter(articlesetarticle__articleset = self.options['articleset'])
            if articles:
                self.options['date'] = articles.aggregate(Min('date'))['date__min'].date()
                self.options['last_date'] = articles.aggregate(Max('date'))['date__max'].date()
            
                self.run_range(_input)


    def run_range(self, _input):
        while self.options['date'] <= self.options['last_date']:
            self._run(_input)
            self.options['date'] += timedelta(days = 1)

    def handle_input(self):
        if self.options["first_date"]:
            if not self.options["last_date"]:
                raise ValueError("provide both first_date and last_date or neither.")

            elif self.options["first_date"] > self.options["last_date"]:
                raise ValueError("first_date must be <= last_date")

            elif self.options["first_date"] == self.options["last_date"]:
                return "single date"

            else:
                return "date range"

        elif self.options["last_date"]:
            raise ValueError("provide both first_date and last_date or neither.")

        else:
            return "whole set"
            

    def _run(self, _input):
        """
        deduplicates given articleset for given date
        """
        log.info("Deduplicating for articleset '{articleset}' at {date}".format(**self.options))

        articles = Article.objects.filter( articlesetarticle__articleset = self.options['articleset'],
                                           date__contains = self.options['date']
            )

        log.info("Selected {n} articles".format(n = len(articles)))

        idDict = {}
        for article in articles:
            identifier = (article.medium_id, article.headline, str(article.date))
            if identifier:
                if not identifier in idDict.keys():
                    idDict[identifier] = []
                idDict[identifier].append(article.id)

        removable_ids = []
        for ids in idDict.values():
            if len(ids) > 1:
                removable_ids.extend(sorted(ids)[1:])

        articles.filter(id__in = removable_ids).update(project = self.options['recycle_bin_project'])
        ArticleSetArticle.objects.filter(article__in = removable_ids).delete()

        log.info("Moved {n} duplications to trash".format(n = len(removable_ids)))



def deduplicate_scrapers(date):
    options = {
        'last_date' : date,
        'first_date' : date - timedelta(days = 7),
        'recycle_bin_project' : 1
        }

    scrapers = Scraper.objects.filter(run_daily='t')
    for s in scrapers:
        options['articleset'] = s.articleset_id
        DeduplicateScript(**options).run(None)

        
if __name__ == '__main__':
    amcatlogging.info_module("amcat.scripts.maintenance.deduplicate")
    from amcat.scripts.tools import cli
    cli.run_cli(DeduplicateScript)
    

###########################################################################  
#                          U N I T   T E S T S                            #  
###########################################################################

from amcat.tools import amcattest    

class TestDeduplicateScript(amcattest.PolicyTestCase):
    def test_deduplicate(self):
        """One article should be deleted from artset and added to project 2"""
        p = amcattest.create_test_project()
        recycle = amcattest.create_test_project()
        art1 = amcattest.create_test_article( headline='blaat1', project=p)
        art2 = amcattest.create_test_article( headline='blaat2', project=p, medium=art1.medium)
        art3 = amcattest.create_test_article( headline='blaat1', project=p, medium=art1.medium)
        artset = amcattest.create_test_set(articles=[art1, art2, art3])
        d = DeduplicateScript(articleset = artset.id, recycle_bin_project=recycle.id)
        d.run( None )
        self.assertEqual(len(artset.articles.all()), 2)
        self.assertEqual(len(Article.objects.filter(project = recycle)), 1)
