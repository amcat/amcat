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
Script for removing html2text tags such as [this one](url) in articles
"""
import logging; log = logging.getLogger(__name__)

import re
from django import forms
from django.db.models import Max

from amcat.scripts.script import Script
from amcat.models.article import Article
from amcat.models.articleset import ArticleSet

#Note: this is only a first version. Do not expect 100% clean articles, for exactly getting it right seems quite hard.
class RemoveHTML2TextForm(forms.Form):
    articleset = forms.ModelChoiceField(ArticleSet.objects.all(), required = True)
    
class RemoveHTML2TextScript(Script):
    options_form = RemoveHTML2TextForm
    def run(self, _input):
        articles = Article.objects.filter(articlesets_set = self.options['articleset'].id)
        for article in articles:
            len_before = len(article.text)
            article.text = self.clean_text(article.text)
            len_after = len(article.text)
            if len_after < 0.50*len_before:
                log.warning("article text truncated by >50%, aborting save")
            else:
                article.save()

    def clean_text(self, text):
        #hyperlinks: doesn't work in various cases. Interestingly, finding urls in text with re is impossible.
        text = re.sub("\[(.*)\]\(.+\)", lambda x: x.group(1), text)
        #images: same story
        text = re.sub("\!\[.*\]\(.+\)", "", text)
        #titles and bold text
        text = "\n".join([line.strip("#* ") for line in text.split("\n")])
        return text

if __name__ == "__main__":
    from amcat.scripts.tools.cli import run_cli
    run_cli(RemoveHTML2TextScript)

