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


class DeduplicateForm(forms.form):
    date = forms.DateField()

class DeduplicateScript(Script):
    options_form = DeduplicateForm

    def run(self):
        """
        Takes an articleset/date as input and removes all duplicated articles from that set/date
        """
        for articleset in Scraper.objects.raw("SELECT articleset FROM scrapers WHERE run_daily='t'"):
            
            date = self.options['date']
            articles = Article.objects.filter(articlesetarticle__articleset=articleset,date__gte=date)
            
            txtDict, texts = {}, set()
            for article in articles:
                text = article.text
                if text:
                    if not text in texts:
                        txtDict[text] = []
                    txtDict[text].append(article.id)
                    texts.add(text)

            removable_ids = []
            for ids in txtDict.itervalues():
                if len(ids) > 1:
                    removable_ids.extend(ids[1:])
            articles.filter(id__in = removable_ids).update(project = 2) #trash project
            ArticleSetArticle.objects.filter(article__in = removable_ids).delete() #delete from article set
            log.info("Moved %s duplicated articles to (trash) project 2" % len(removable_ids))
    
        
    def run_scrapers(self):
        """
        Runs on all daily scraper articlesets
        """
        
        
        
if __name__ == '__main__':
    from sys import argv
    from getopt import getopt
    opts,args = getopt(argv,"s")
    for opt,arg in opts:
        if opt == '-s':
            dedu = DeduplicateScript()
            dedu.run_scrapers()
    

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
