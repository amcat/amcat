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
import logging; log = logging.getLogger(__name__)
from amcat.tools import amcatlogging
from datetime import timedelta

class DeduplicateForm(forms.Form):
    date = forms.DateField()
    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
    
class DeduplicateScript(Script):
    options_form = DeduplicateForm

    def run(self,_input):
        """
        deduplicates all scraper articlesets
        """
        log.info("Deduplicating for articleset '{}' at {}".format(
                self.options['articleset'],
                self.options['date']))

        articles = Article.objects.filter(
            articlesetarticle__articleset = self.options['articleset'],
            date = self.options['date']
            )

        log.info("Selected {} articles".format(len(articles)))

        idDict = {}
        for article in articles:
            identifier = article.text + str(article.date)
            if identifier:
                if not identifier in idDict.keys():
                    idDict[identifier] = []
                idDict[identifier].append(article.id)

        removable_ids = []
        for ids in idDict.values():
            if len(ids) > 1:
                removable_ids.extend(sorted(ids)[1:])

        articles.filter(id__in = removable_ids).update(project = 2) #trash project
        ArticleSetArticle.objects.filter(article__in = removable_ids).delete()

        log.info("Moved {} duplications to trash".format(len(removable_ids)))


class DeduplicatePeriodForm(forms.Form):
    first_date = forms.DateField()
    last_date = forms.DateField()
    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())

class DeduplicatePeriod(DeduplicateScript):
    options_form = DeduplicatePeriodForm

    def run(self, _input):
        date = self.options['first_date']
        while date <= self.options['last_date']:
            self.options['date'] = date
            super(DeduplicatePeriod, self).run(_input)
            date += timedelta(days = 1)

class DeduplicateArticlesetForm(forms.Form):
    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())

class DeduplicateArticleset(DeduplicatePeriod):
    options_form = DeduplicateArticlesetForm
    
    def run(self, _input):
        articles = Article.objects.filter(articlesetarticle__articleset = self.options['articleset'])
        self.options['first_date'] = articles.aggregate(Min('date'))[1].date()
        self.options['last_date'] = articles.aggregate(Max('date'))[1].date()
        super(DeduplicateArticleset, self).run(_input)


def deduplicate_scrapers(date):
    scrapers = Scraper.objects.filter(run_daily='t')
    for s in scrapers:
        d = DeduplicatePeriod(first_date = date - timedelta(days=7),
                          last_date = date,
                          articleset = s.articleset_id)
        d.run(None)


        
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
        art1 = amcattest.create_test_article( url='blaat1', project=p)
        art2 = amcattest.create_test_article( url='blaat2', project=p)
        art3 = amcattest.create_test_article( url='blaat1', project=p)
        artset = amcattest.create_test_set(articles=[art1, art2, art3])
        d = DeduplicateScript(articleset = artset.id)
        d.run( None )
        self.assertEqual(len(artset.articles.all()), 2)
        self.assertEqual(len(Article.objects.filter(project = 2)), 1)
