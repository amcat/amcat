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
from functools import partial

from django import forms

from amcat.scripts.script import Script
from amcat.tools.amcatsolr import Solr, filters_from_form
from amcat.tools.table.table3 import Table
from amcat.models import ArticleSet

class Query(Script):
    class options_form(forms.Form):
        articlesets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.all())
        query = forms.CharField()
    output_type = Table
    
    def run(self, _input=None):
        filters = filters_from_form(self.options)
        query = self.options['query']
        t = Table(rows = Solr().query_all(query, filter=filters, fields=["id"]),
                  columns = ["id", "score"],
                  cellfunc = dict.get)
        return t
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    print result.output()
        
