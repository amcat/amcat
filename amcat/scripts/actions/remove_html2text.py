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
Script for removing html2text tags such as [link]this one[/link] in articles
"""
import re
from django import forms
from django.db.models import Max

from amcat.scripts.script import Script
from amcat.models.article import Article
from amcat.models.articleset import ArticleSet

class RemoveHTML2TextForm(forms.Form):
    articleset = forms.ModelChoiceField(ArticleSet.objects.all(), required = False)
    
class RemoveHTML2TextScript(Script):
    def run(self, _input):
        articles = Article.objects.filter(articlesetarticle__articleset = self.options['articleset'].id)
        for article in articles:
            article.text = self.clean_text(article.text)
        #article.save()

    def clean_text(self, text):
        pass
        

if __name__ == "__main__":
    #testing
    article = Article.objects.get(id=9192776)
    script = RemoveHTML2TextScript()
    text = script.clean_text(article.text)
    print(text)

