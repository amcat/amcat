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
Script to get queries for a codebook
"""

import logging; log = logging.getLogger(__name__)

from django import forms
from django.db import transaction

from amcat.models import AnalysedArticle
from amcat.scripts.script import Script

PLUGINTYPE_PARSER=1

class CheckParsing(Script):
    class options_form(forms.Form):
        pass
                                        
    def _run(self):
        while True:
            to_check = list(AnalysedArticle.objects.filter(done=False, error=False).select_related("plugin")[:10])
            to_check = [AnalysedArticle.objects.get(pk=2252)]
            if not to_check: break
            
            for aa in to_check:
                parser = aa.plugin.get_class()()
                print(aa.info, parser.retrieve_article(aa))
            break

        
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()

