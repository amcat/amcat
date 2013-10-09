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
Script that retrieves basic information of a search query, such as number of matching articles and the first/last date of the matching articles
"""

from amcat.scripts import script, types
from amcat.tools import keywordsearch
from django.db.models import Min, Max
from amcat.models.medium import Medium
import amcat.scripts.forms
from django import forms

import logging
log = logging.getLogger(__name__)


class ArticleSetStatisticsScript(script.Script):
    input_type = None
    options_form = amcat.scripts.forms.SelectionForm
    output_type = types.ArticleSetStatistics

    def run(self, input=None):
        return keywordsearch.get_statistics(self.options)
        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(ArticleSetStatisticsScript)

