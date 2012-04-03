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
Script add a codebook
"""

import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.models.coding.codebook import Codebook

PROJECT_ROLE_READER=11

class AddCodebookForm(forms.ModelForm):
    class Meta:
        model = Codebook
        fields = ['name']


class AddCodebook(Script):
    """Add a project to the database."""

    options_form = AddCodebookForm
    output_type = Codebook

    def run(self, _input=None):
        raise Exception("!")

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAddCodebook(amcattest.PolicyTestCase):
    pass
