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
Find duplicate articles in a given project and remove them
"""

from django import forms

from amcat.scripts.script import Script
from amcat.models.project import Project
from amcat.models.article import Article
from amcat.models.articleset import ArticleSetArticle, ArticleSet

class DeduplicateForm(forms.Form):
    project = forms.ModelChoiceField(queryset = Project.objects.all())
    first_date = forms.DateField()
    last_date = forms.DateField()

class DeduplicateScript(Script):
    options_form = DeduplicateForm
    def run(self, _input=None):
        articles = Article.objects.filter(
            project = self.options['project'].id,
            date__gte = self.options['first_date'],
            date__lte = self.options['last_date']
            ).order_by('date','medium')

        # Reduce articles to chunks of ~1000
        for chunk in self._per_medium(articles):
            medium = chunk[0].medium; date = chunk[0].date.date()
            print("{} at {}: {} articles".format(medium,date,len(chunk)))
            for duplicates in self._getdupes(chunk).values():
                if len(duplicates) > 1:
                    headline = duplicates[0].headline.encode('utf-8')
                    print("{} dupes: {}".format(len(duplicates), headline))
                    self._deduplicate(duplicates)
        
    def _per_medium(self, articles):
        group = []
        last_key = None
        for article in articles:
            key = (article.date, article.medium.id)
            if last_key and key != last_key:
                yield group
                group = [article]
            else:
                group.append(article)
            last_key = key

    def _getdupes(self, articles):
        sets = {}
        for article in articles:
            key = self._articlekey(article)
            if key not in sets.keys():
                sets[key] = [article]
            else:
                sets[key].append(article)
        return sets
            

    def _articlekey(self, article):
        """When an article shares all of these props with another, it's considered a duplicate"""
        return (article.date,
                article.medium.id,
                article.headline,
                article.parent and article.parent.id,
                article.author,
                article.text)
                
    def _deduplicate(self, articles):
        # Keep one article
        keep = self._select_article(articles)
        articles.remove(keep)

        # Put kept article in all sets
        setids = set([asa.articleset_id for asa in ArticleSetArticle.objects.filter(article__in=articles)])
        sets = ArticleSet.objects.filter(pk__in = setids)
        [s.add(keep) for s in sets]

        # Remove leftovers
        ArticleSetArticle.objects.filter(article__in = articles).delete()
        Article.objects.filter(pk__in = [a.id for a in articles]).update(project=1)
    
    def _select_article(self, articles):
        """Select an article to keep"""
        ids = [a.id for a in articles]
        return [a for a in articles if a.id == min(ids)][0]

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(DeduplicateScript)
