#!/usr/bin/python
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
Script run a preprocessing analysis against a remote (REST) database
"""

import logging
import json

from amcat.scripts.script import Script
from amcat.scripts.actions.add_tokens import AddTokens
from amcat.scripts.actions.get_analysis_articles import GetAnalysisArticles
from amcat.tools.rest import Rest
from amcat.tools import classtools

log = logging.getLogger(__name__)

from django import forms


class RemoteAnalysisForm(forms.Form):
    analysis_id = forms.IntegerField()
    host = forms.CharField()
    narticles = forms.IntegerField(required=False, initial=10)

class RemoteAnalysis(Script):
    """Add a project to the database."""

    options_form = RemoteAnalysisForm
    output_type = None

    def __init__(self, options=None, **kargs):
        super(RemoteAnalysis, self).__init__(options, **kargs)
        self.rest = Rest(host=self.options['host'])
        self.analysis_id = self.options['analysis_id']
        self.narticles = self.options['narticles']

    def run(self, _input=None):
        self.script = self.get_analysis_script()
        articles = self.get_articles()
        log.info("Retrieved {n} articles to analyse".format(n=len(articles)))
        print(articles)
        for article in articles:
            self.analyse_article(article["id"])

    def get_articles(self):
        return self.rest.call_action(GetAnalysisArticles, analysis=self.analysis_id, narticles=self.narticles)

    def get_analysis_script(self):
        analysis = self.rest.get_object("analysis", self.analysis_id)
        plugin = analysis["plugin"]
        return classtools.import_attribute(plugin["module"], plugin["class_name"])(analysis)

    def analyse_article(self, analysis_article_id):
        sentences = self.get_sentences(analysis_article_id)
        log.info("Analysing {n} sentences from article {analysis_article_id}"
                  .format(n=len(sentences), **locals()))
        tokens, triples = self.script.process_sentences(sentences)
        log.info("Storing {ntok} tokens and {ntrip} triples for article_analysis"
                 "{analysis_article_id}".format(ntok=len(tokens),
                 ntrip=len(triples), **locals()))
        if not tokens: raise Exception()
        self.rest.call_action(AddTokens, analysisarticle=analysis_article_id,
                              tokens=json.dumps(tokens),
                              triples=json.dumps(triples))


    def get_sentences(self, analysis_article_id):
        return [(int(s["id"]), s["sentence"]["sentence"]) for s in
                self.rest.get_objects("analysissentence",
                                      analysis_article=analysis_article_id,
                                      limit=9999)]


    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    from amcat.tools import amcatlogging
    #amcatlogging.debug_module("amcat.tools.rest")
    amcatlogging.debug_module()


    cli.run_cli()
