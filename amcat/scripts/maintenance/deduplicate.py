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
import re, collections

class DeduplicateForm(forms.Form):
    slow = forms.BooleanField(required = False, initial=False)   
    keep_latest = forms.BooleanField(required = False, initial = False)
    ignore_medium = forms.BooleanField(required = False, initial = False)
    test = forms.BooleanField(required = False, initial=False)   
    printout = forms.BooleanField(required = False, initial=False)   
    first_date = forms.DateField(required = False)
    last_date = forms.DateField(required = False)    
    articleset = forms.ModelChoiceField(queryset = ArticleSet.objects.all())
    
class DeduplicateScript(Script):
    options_form = DeduplicateForm

    def run(self, _input=None):
        articles = self.options['articleset'].articles.all()
        if not articles.exists():
            log.info("Set {aset.id} is empty, no dedpulication needed!".format(aset=self.options['articleset']))
            return
        mode = self.handle_input()
        if mode == "date range":
            self.options['date'] = self.options['first_date']
            self.run_range(self.options['first_date'], self.options['last_date'])

        elif mode == "single date":
            self._run_date(self.options['first_date'])

        elif mode == "whole set":
            log.info("Getting dates")
            dates = articles.dates('date', 'day')
            log.info("Deduplicating {n} dates".format(n=len(dates)))
            for date in dates:
                self._run_date(date)

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
            

    def run_range(self, start, end):
        date = start
        while date <= end:
            self._run_date(date)
            date += timedelta(days = 1)
            
    def _run_date(self, date):
        """
        deduplicates given articleset for given date
        """
        from django.db import connection
        connection.queries = []
        
        articleset = self.options['articleset']
        log.info("Deduplicating for articleset '{articleset}' at {date}".format(**locals()))

        articles = articleset.articles.filter(date__gte = date, date__lt = date + timedelta(days=1))
        if self.options['ignore_medium']:
            articles = articles.only("date", "headline")
        else:
            articles = articles.only("date", "medium", "headline")
        articles = list(articles)

        # get text hash for articles with missing or nonsensical headlines
        no_headline = [a.id for a in articles if (not a.headline) or (a.headline in ('missing', 'no headline', 'Kort nieuws'))]
        texts = dict(Article.objects.filter(pk__in=no_headline).extra(select={'texthash':'md5(text)'}).values_list('id', 'texthash'))
        
        log.info("Selected {n} articles".format(n = len(articles)))

        arDict = collections.defaultdict(list)
        for article in articles:
            if self.options['ignore_medium']:
                identifier = (texts.get(article.id, article.headline), str(article.date.date()))
            else:
                identifier = (texts.get(article.id, article.headline), str(article.date.date()), article.medium_id)
            arDict[identifier].append(article)
        
        removable_ids = []
        for arts in arDict.values():
            arts = sorted(arts, key=self.score)
            removable_ids.extend(a.id for a in arts[:-1]) # keep the last one, it has highest score
        
        if self.options['printout']:
            self.printout(articles, removable_ids)
        
        if not self.options['test']:
            ArticleSetArticle.objects.filter(article__in = removable_ids).delete()
        
        log.info("Removed {n} duplications from articleset".format(n = len(removable_ids)))

    def printout(self, articles, removable_ids):
        """Print the given articles to a csv file to facilitate checking"""
        import csv, sys
        w = csv.writer(sys.stdout)
        if not getattr(self, 'csv_header_printed', False):
            w.writerow(["aid", "date", "medium", 'headline', 'len(text)', 'text[:100]', 'delete?'])
            self.csv_header_printed = True
        for a in sorted(articles, key=lambda a : (a.date, a.medium_id, a.headline, a.id)):
            w.writerow([a.id, a.date, a.medium_id, a.headline.encode('ascii','replace'), len(a.text), `a.text[:100]`, a.id in removable_ids])


    def score(self, article):
        """
        Determines the score for an article of the given articles gets to stay, where the highest score will be kept.
        Sometimes a later article has a better quality (extra metadata) because of scraper fixes/improvements.
        If not, it is better to keep the old article because of possible codings attached to it
        """
        if self.options['slow']:
            # has_html2text?
            p = re.compile("\[.+\]\(.+\)")
            matches = p.search(article.text)
            has_html2text = 1 if matches else 0
            
            #determine the highest amount of fields in the articles
            n_fields = len([f for f in article._meta.get_all_field_names() if f != 'metastring' and getattr(article, f, None) is not None])
            n_fields += article.metastring.count(":")
            
            return (has_html2text, n_fields, len(article.text), -article.id)
        elif self.options['keep_latest']:
            return article.id
        else:
            return -article.id
        
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

        m = amcattest.create_test_medium()
        
        art2 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p, 
            medium=m,
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


        
        art1 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p,
            text="""
bla bla bla
[bla](http://www.bla.com) bla bla bla
""",
            date = m_date(2012,01,01),
            section = "kaas",
            metastring = {'moet_door':True,'delete?':False,'mist':'niets'},
            medium=m,
            )

        art3 = amcattest.create_test_article( 
            headline='blaat1', 
            project=p, 
            medium=m,
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
            medium=m,
            text = """
bla bla bla
[bla](http://www.bla.com) bla bla bla
""",
            date = m_date(2012,01,01),
            section = "kaas",
            metastring = {'moet_door':False,'delete?':True,'mist':'later gemaakt'}
            )

        artset = amcattest.create_test_set(articles=[art1, art2, art3, art4])
        d = DeduplicateScript(articleset = artset.id, slow=True)
        d.run( None )
        self.assertEqual(len(artset.articles.all()), 1)
        self.assertEqual(len(Article.objects.filter(project = p)), 4)
        self.assertEqual(art1.pk, artset.articles.all()[0].pk)
