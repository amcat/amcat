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

#from amcat.tools import dbtoolkit
from amcat.scripts.script import Script
from amcat.models import Medium, Article, MediumAlias


class ReplaceMedium(Script):
    """
    Globally (!) replace a medium by another medium, delete the old medium,
    and add its name as an alias for the new medium.

    Warning: This potentiall affects all projects in the database and cannot be undone
             It should ONLY be used to fix mistakes/typos, e.g. "vk.nl" ->"volkskrant.nl"
             It should NOT be used to merge two versions of the same medium,
                 e.g. volkskrant and volkskrant.nl
    """

    class options_form(forms.Form):
        old_medium = forms.ModelChoiceField(queryset=Medium.objects.all())
        new_medium = forms.ModelChoiceField(queryset=Medium.objects.all())

    def _run(self, old_medium, new_medium):
        arts = Article.objects.filter(medium=old_medium)
        log.info("Replacing medium {old_medium.id}:{old_medium} -> {new_medium.id}:{new_medium} in {n} articles"
                 .format(n=arts.count(), **locals()))
        arts.update(medium=new_medium)
        log.info("Deleting medium {old_medium.id}:{old_medium}".format(**locals()))
        old_medium.delete()
        log.info("Inserting {old_medium} as alias for {new_medium.id}:{new_medium}".format(**locals()))
        MediumAlias.objects.create(medium=new_medium, name=old_medium.name)
        log.info("Done")
    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()
