#!/usr/bin/python

##########################################################################
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
Script to clean the index for a project
"""

import logging; log = logging.getLogger(__name__)

import solr
from django import forms

from amcat.models import Project, ArticleSet, Article, ArticleSetArticle
from amcat.models.analysis import add_to_queue
from amcat.scripts.script import Script
from amcat.tools.amcatsolr import Solr
from amcat.tools.toolkit import splitlist


class SolrCleanForm(forms.Form):
    projects = forms.ModelMultipleChoiceField(queryset=Project.objects.all(), required=False)
    sets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.all(), required=False)
    include_project_sets = forms.BooleanField(initial=False, required=False)
    batch = forms.IntegerField(required=False)

    def clean(self):
        data = super(SolrCleanForm, self).clean()
        if not data['projects'] and not data['sets']:
            raise forms.ValidationError("Please list the projects or sets to clean")
        return data
        
class SolrClean(Script):
    options_form = SolrCleanForm

    def run(self, _input):
        projects, sets = list(self.options["projects"]), list(self.options["sets"])
        if self.options["include_project_sets"]:
            sets += list(ArticleSet.objects.filter(project__in=projects))
        log.info("Cleaning projects {projects}, sets {sets}".format(**locals()))

        articles = set()
        if projects:
            q = Article.objects.filter(project__in=projects)
            articles |= set(aid for (aid,) in q.values_list("id"))
        if sets:
            q = ArticleSetArticle.objects.filter(articleset__in=sets)
            articles |= set(aid for (aid,) in q.values_list("article_id"))

        if self.options["batch"]:
            log.info("Cleaning {n} articles in {m} batch(es) of {b}"
                     .format(n=len(articles), b=self.options["batch"],
                             m=1 + len(articles) // self.options["batch"]))
            for i, articles in enumerate(splitlist(articles, self.options["batch"])):
                log.info("Batch {i}: Cleaning {n} articles".format(n=len(articles), **locals()))
                Solr().add_articles(articles)
        else:
            log.info("Cleaning {n} articles".format(n=len(articles)))
            Solr().add_articles(articles)
        
        log.info("Done!")

        #TODO: also delete articles that should be deleted...

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
