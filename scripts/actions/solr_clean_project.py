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

from amcat.models.project import Project
from amcat.models.article import Article
from amcat.models.article_preprocessing import add_to_queue

from amcat.scripts.script import Script

BATCH = 100
def get_articleids(projectid):
    query = "projectid:{projectid}".format(**locals())
    s = solr.Solr('http://localhost:8983/solr')

    start =0
    while True:
        result =s.select(query,fields=["id"],score=False, start=start, rows=BATCH).results
        if not result: break
        for row in result:
            yield row["id"]
        start += BATCH

class CleanProjectForm(forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.all())


class CleanProject(Script):
    options_form = CleanProjectForm

    def run(self, _input):
        project = self.options["project"]
        log.info("Cleaning project {project.id} : {project}".format(**locals()))
        log.debug("Getting article list from db")
        db_ids = set(aid for (aid,) in Article.objects.filter(project=project).values_list("id"))
        log.debug("Retrieved {n} articles, getting list of articles to add or delete"
                  .format(n=len(db_ids)))
        to_delete = []
        for id in get_articleids(project.id):
            try:
                db_ids.remove(id)
            except KeyError:
                to_delete.append(id)

        log.info("Deleting {} articles from index".format(len(to_delete)))
        if to_delete:
            s = solr.SolrConnection(b'http://localhost:8983/solr')
            s.delete_many(to_delete)
            s.commit()
        log.info("Adding {} articles to be checked".format(len(db_ids)))
        if db_ids:
            add_to_queue(*db_ids)

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
