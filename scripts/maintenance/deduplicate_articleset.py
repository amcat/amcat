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

from amcat.scripts.script import Script
from amcat.scripts.tools import cli

from amcat.models.article import Article
from amcat.models.scraper import Scraper
from amcat.models.articleset import ArticleSet, ArticleSetArticle
import logging; log = logging.getLogger(__name__)
from amcat.tools import amcatlogging
from django.db.models import Min
from datetime import date,timedelta

class DeduplicateAsetForm(forms.Form):
    articleset = forms.CharField()

class DeduplicateScript(Script):
    options_form = DeduplicateAsetForm

    def run(self,_input):
        """
        Takes an articleset as input and removes all duplicated articles from that set
        """
        
        
        articleset=self.options['articleset']
        allarticles = Article.objects.filter(articlesetarticle__articleset=articleset)
        dates = sorted(set([d['date'].date() for d in Article.objects.filter(articlesetarticle__articleset=articleset).order_by('date').values('date').distinct()]))
        print("dates: {}".format(len(dates)))
        for _date in dates:
            articles = allarticles.filter(date__year=_date.year,
                                          date__month=_date.month,
                                          date__day=_date.day)
            log.info("Selected {} articles for date {}".format(len(articles),_date))
            artDict, knownarticles = {}, set()
            for article in articles:
                text = article.text
                headline = article.headline
                artdate = article.date

                distinct = headline+str(artdate)+text
                if distinct:
                    if not distinct in knownarticles:
                        artDict[distinct] = []
                    artDict[distinct].append(article.id)
                    knownarticles.add(distinct)

            removable_ids = []
            for ids in artDict.itervalues():
                if len(ids) > 1:
                    removable_ids.extend(ids[1:])
            articles.filter(id__in = removable_ids).update(project = 2) #trash project
            ArticleSetArticle.objects.filter(article__in = removable_ids).delete() #delete from article set
            log.info("Moved {} duplicated articles to (trash) project 2 for date {}".format(len(removable_ids),_date))
            _date += timedelta(days=1)
        
        
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
