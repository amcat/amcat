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
Assess the quality of articles in a given set at a given date
"""

from django import forms
import logging; log = logging.getLogger(__name__)
import json

from amcat.scripts.script import Script
from amcat.models.articleset import ArticleSet
from amcat.models.article import Article

class ValueArticleForm(forms.Form):
    date = forms.DateField()
    articleset = forms.ModelChoiceField(queryset = ArticleSet.objects.all())

class ValueArticleScript(Script):
    options_form = ValueArticleForm
    article_properties = [
        'date','section',
        'pagenr','headline','byline',
        'length','url','text','parent',
        'medium','author'
        ]
    def __init__(self, *args, **kwargs):
        super(ValueArticleScript, self).__init__(*args, **kwargs)
        self.article_props_occurrences = {prop : 0 for prop in self.article_properties}
        

    def run(self, _input=None):
        articles = Article.objects.filter(
            date = self.options['date'],
            articlesetarticle__articleset = self.options['articleset'])
        for article in articles:
            print
            print(article.headline)

            #evaluate regular properties
            for prop in self.article_properties:
                if hasattr(article, prop):
                    value = getattr(article, prop)
                else:
                    value = None
                if value:
                    self.article_props_occurrences[prop] += 1
                print("{prop} : {v}".format(v = self.truncate(value), **locals()))

            #evaluate metastring
            for key, value in eval(article.metastring).items():
                print("meta.{key} : {v}".format(v = self.truncate(value), **locals()))
                if key in self.article_props_occurrences.keys():
                    self.article_props_occurrences[key] += 1
                else:
                    self.article_props_occurrences[key] = 1

        #print totals
        print("\n\tTotal:\n")
        print("{key}: {value} / {total articles} = {percentage}")
        total_articles = len(articles)
        for key, value in self.article_props_occurrences.items():
            percentage = int((float(value) / float(total_articles)) * 100)
            print("{key}: {value} / {total_articles} = {percentage}%".format(**locals()))

    def truncate(self, value):
        value = unicode(value)
        value = " ".join(value.split("\n"))
        if len(value) > 80:
            value = value[0:79] + "..."
        return value.encode('utf-8')
        

if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(ValueArticleScript)
