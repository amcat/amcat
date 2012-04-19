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

import logging;
from amcat.models import Analysis
from amcat.scripts.script import Script
from amcat.tools.rest import Rest
from amcat.tools import classtools

log = logging.getLogger(__name__)

from django import forms


class RemoteAnalysisForm(forms.Form):
    analysis_id = forms.IntegerField()
    host = forms.CharField()

class RemoteAnalysis(Script):
    """Add a project to the database."""

    options_form = RemoteAnalysisForm
    output_type = None

    def __init__(self, options=None, **kargs):
        super(RemoteAnalysis, self).__init__(options, **kargs)
        self.rest = Rest(host=self.options['host'])

    def run(self, _input=None):
        script = self.get_analysis_script()
        articles = self.get_articles(script.analysis['id'])
        log.info("Retrieved {n} articles to analyse".format(n=len(articles)))
        for article in articles:
            self.analyse_article(article)

    def get_articles(self, analysis_id):
        return [a["article"] for a in
                self.rest.get_objects("articleanalysis", analysis = analysis_id,
                    done = False, prepared = True, delete=False, )]

    def get_analysis_script(self):
        analysis = self.rest.get_object("analysis", self.options['analysis_id'])
        plugin = analysis["plugin"]
        script = classtools.import_attribute(plugin["module"], plugin["class_name"])(analysis)
        return script

    def analyse_article(self, article):
        log.info("Analysing article {article}".format(**locals()))
        for sid, sentence in self.get_sentences(article):
            print(sid, sentence)

    def get_sentences(self, article):
        return [(s["id"], s["sentence"])
                for s in self.rest.get_objects("sentence", article=article)]

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    from amcat.tools import amcatlogging
    amcatlogging.debug_module("amcat.tools.rest")


    cli.run_cli()