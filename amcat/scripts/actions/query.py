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


import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.tools.table.table3 import Table
from amcat.models import ArticleSet

from amcat.tools.amcates import ES

class Query(Script):
    """
    Perform a keyword query on an articleset.
    """

    class options_form(forms.Form):
        articlesets = forms.ModelMultipleChoiceField(queryset=ArticleSet.objects.all())
        query = forms.CharField()
    output_type = Table
   
    def run(self, _input=None):
        sets = self.options['articlesets'].values_list("id", flat=True)

        rows = ES().query(
            query=self.options["query"],
            filters=dict(sets=list(sets)),
        )

        return Table(rows=rows, columns=("id", "score"), cellfuc=dict.get)
   
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    print result.output()

