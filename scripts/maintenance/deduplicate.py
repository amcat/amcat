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
from amcat.models.articleset import ArticleSet, ArticleSetArticle
import logging; log = logging.getLogger(__name__)
from amcat.tools import amcatlogging

TRASH_PROJECT_ID=2

class DeduplicateForm(forms.Form):
    """Form for DeduplicateScript"""
    articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
    date = forms.DateField(required=False)

class DeduplicateScript(Script):
    options_form = DeduplicateForm
    
    def run(self, _input):
        """
        Takes an articleset as input and removes all duplicated articles from that set
        """
        asid = self.options['articleset'] # articleset id
        articles = Article.objects.filter( articlesetarticle__articleset = asid)
        if self.options['date']:
            articles = articles.filter(date__gte=self.options['date'])

        log.info("Retrieving all medium / date combinations")
        medium_dates = articles.values_list("medium_id", "date").distinct()

        n = len(medium_dates)
        log.info("Checking {n} medium/date combinations".format(**locals()))

        duplicates = set()
        
        for i, (medium, date) in enumerate(medium_dates):
            art_list = articles.filter(medium_id=medium, date=date).values_list("id", "length", "headline")
            log.info(" {i}/{n} Checking {nart} articles in medium: {medium}, date: {date}"
                     .format(nart=len(art_list), **locals()))

            seen_keys = {}
            ndup = 0
            for aid, length, headline in art_list:
                key = (length, headline)
                if key in seen_keys:
                    log.debug("    Duplicate: {aid} = {}".format(seen_keys[key], **locals()))
                    duplicates.add(aid)
                    ndup += 1
                else:
                    seen_keys[key] = aid

            if ndup:
                log.info("  Found {ndup} duplicates, |duplicates| now {}".format(len(duplicates), **locals()))
        log.info("Moving {n} duplicates to trash".format(n=len(duplicates)))
              
        articles.filter(id__in = duplicates).update(project = TRASH_PROJECT_ID) 
        ArticleSetArticle.objects.filter(article__in = duplicates).delete() 


if __name__ == '__main__':
    cli.run_cli()

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
