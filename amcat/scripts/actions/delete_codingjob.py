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
Script add a project
"""

import logging; log = logging.getLogger(__name__)

from django import forms
from django.db import transaction

from amcat.scripts.script import Script
from amcat.models import CodingJob



PROJECT_ROLE_READER=11

class DeleteCodingJob(Script):
    """Delete the given job including all codings and article set unless the
    article set is in use somewhere else"""
    class options_form(forms.Form):
        job = forms.ModelChoiceField(queryset=CodingJob.objects.all())

    @transaction.atomic
    def run(self, _input=None):
        j = self.options['job']

        # remember article set so we can delete it later
        aset = j.articleset
        j.delete()
        if not CodingJob.objects.filter(articleset=aset).exists():
            aset.delete()

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
