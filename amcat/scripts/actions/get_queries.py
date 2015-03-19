#!/usr/bin/python

# ##########################################################################
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
Script to get queries for a codebook
"""

import logging

log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.models.coding.codebook import Codebook
from amcat.tools.table.table3 import Table, ObjectTable

LABEL_LANGUAGE = 2, 1,
QUERY_LANGUAGE = 13,


class GetQueries(Script):
    class options_form(forms.Form):
        codebook = forms.ModelChoiceField(queryset=Codebook.objects.all())

    output_type = Table

    def run(self, _input=None):
        c = self.options["codebook"]
        for lang in LABEL_LANGUAGE + QUERY_LANGUAGE:
            c.cache_labels(lang)
        t = ObjectTable(rows=c.get_codes())
        t.addColumn(lambda c: c.id, "id")
        t.addColumn(lambda c: c.get_label(*LABEL_LANGUAGE), "label")
        t.addColumn(lambda c: c.get_label(*QUERY_LANGUAGE, fallback=False), "query")
        return t


if __name__ == '__main__':
    from amcat.scripts.tools import cli

    result = cli.run_cli()
    #print result.output()

