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
from amcat.tools import amcatlogging

import logging; log = logging.getLogger(__name__)
from datetime import timedelta
from datetime import date as m_date
import re

class DeduplicateForm(forms.Form):
    first_date = forms.DateField(required = False)
    last_date = forms.DateField(required = False)    
    articleset = forms.ModelChoiceField(queryset = ArticleSet.objects.all())
    
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
            self.options['date'] = articles.aggregate(Min('date'))['date__min'].date()
            self.options['last_date'] = articles.aggregate(Max('date'))['date__max'].date()
            log.info("first date: {mi}; last date: {ma}".format(mi = self.options['date'], ma = self.options['last_date']))
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

        arDict = {}
        for article in articles:
            if article.headline:
                identifier = (article.headline, str(article.date.date()), article.medium)
            else:
                identifier = (article.text, str(article.date), article.medium)
                
            if identifier:
                if not identifier in arDict.keys():
                    arDict[identifier] = []
                arDict[identifier].append(article)

        removable_ids = []
        for articles in arDict.values():
            keep = self.compare(articles)
            removable_ids.extend([a.pk for a in articles if a.pk != keep.pk])
            
        ArticleSetArticle.objects.filter(article__in = removable_ids).delete()
        log.info("Removed {n} duplications from articleset".format(n = len(removable_ids)))


    def compare(self, articles):
        """
        Determines which article of the given articles gets to stay. 
        Sometimes a later article has a better quality (extra metadata) because of scraper fixes/improvements.
        If not, it is better to keep the old article because of possible codings attached to it
        """

        #check which articles have been through html2text
        has_html2text = []
        for article in articles:
            p = re.compile("\[.+\]\(.+\)")
            matches = p.search(article.text)
            if matches:
                has_html2text.append(article)
        #if any, let those go first
        if has_html2text:
            articles_2 = has_html2text
        else:
            articles_2 = articles
        #determine the highest amount of fields in the articles
        n_fields = 0
        for article in articles_2:
            l = 0
            for field in [getattr(article, f) for f in article._meta.get_all_field_names() if f != 'metastring' and hasattr(article, f)]:


                if field != None:
                    l += 1
            if article.metastring:
                l += len(eval(article.metastring))
            if l > n_fields:
                n_fields = l
                    

        #filter out the articles with less fields
        articles_3 = []
        for article in articles_2:
            le = 0
            for field in [getattr(article, f) for f in article._meta.get_all_field_names() if f != 'metastring' and hasattr(article, f)]:
                if field != None:
                    le += 1
            if article.metastring:
                le += len(eval(article.metastring))

            if le == n_fields:
                articles_3.append(article)

        #if still multiple articles, pick article with longest text    
        l_text = -1
        for article in articles_3:
            if len(article.text) > l_text:
                l_text = len(article.text)

        articles_4 = []
        for article in articles_3:
            if len(article.text) == l_text:
                articles_4.append(article)


        #if still multiple, pick out oldest version
        article_ids = sorted([article.pk for article in articles_4])
        for article in articles_4:
            if article.id == article_ids[0]:
                return article


def deduplicate_scrapers(date):
    options = {
        'last_date' : date,
        'first_date' : date - timedelta(days = 7),
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

        art1 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p,
            text="""
bla bla bla
[bla](http://www.bla.com) bla bla bla
""",
            date = m_date(2012,01,01),
            section = "kaas",
            metastring = {'moet_door':True,'delete?':False,'mist':'niets'}
            )


        art2 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p, 
            medium=art1.medium,
            text = """
bla bla bla
bla bla bla bla


var c=0;
var t;
var timer_is_on=0;

function timedCount()
{
document.getElementById('txt').value=c;
c=c+1;
t=setTimeout(function(){timedCount()},1000);
}

function doTimer()
{
if (!timer_is_on)
  {
  timer_is_on=1;
  timedCount();
  }
}

function stopCount()
{
clearTimeout(t);
timer_is_on=0;
}
""",
            date = m_date(2012,01,01),
            section = "kaas",
            metastring = {'moet_door':False,'delete?':True,'mist':'link, heeft wel meer tekst'}
            )


        art3 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p, 
            medium=art1.medium,
            text="""
bla bla bla
[bla](http://www.bla.com) bla bla bla
""",
            date = m_date(2012,01,01),
            metastring = {'mist':'3 fields'}
            )
        
        art4 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p, 
            medium=art1.medium,
            text = """
bla bla bla
[bla](http://www.bla.com) bla bla bla
""",
            date = m_date(2012,01,01),
            section = "kaas",
            metastring = {'moet_door':False,'delete?':True,'mist':'later gemaakt'}
            )

        artset = amcattest.create_test_set(articles=[art1, art2, art3, art4])
        d = DeduplicateScript(articleset = artset.id)
        d.run( None )
        self.assertEqual(len(artset.articles.all()), 1)
        self.assertEqual(len(Article.objects.filter(project = p)), 4)
        self.assertEqual(art1.pk, artset.articles.all()[0].pk)
