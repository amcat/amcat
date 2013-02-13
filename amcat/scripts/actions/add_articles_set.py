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
Script for adding articles from one set to another
"""

import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.models.articleset import ArticleSet
from amcat.models.article import Article
from amcat.scripts.script import Script

class MoveArticlesForm(forms.Form):
    from_set = forms.ModelChoiceField(queryset = ArticleSet.objects.all())
    to_set = forms.ModelChoiceField(queryset = ArticleSet.objects.all())

class MoveArticles(Script):
    options_form = MoveArticlesForm

    def run(self, _input):
        fr = self.options['from_set']
        to = self.options['to_set']


        log.debug("getting articles...")
        articles = list(Article.objects.filter(
            articlesetarticle__articleset = fr.id))
        n = len(articles)

        log.debug("...done. {n} articles found".format(**locals()))


        log.debug("adding articles to new set...")
        to.add_articles(articles)
        to.save()
        
        log.info("moved {n} articles from {fr} to {to}".format(**locals()))


if __name__ == "__main__":
    from amcat.scripts.tools import cli
    cli.run_cli(MoveArticles)
