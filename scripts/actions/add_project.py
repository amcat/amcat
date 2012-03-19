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
Script add a project
"""

import logging; log = logging.getLogger(__name__)

from django import forms

from amcat.scripts.script import Script
from amcat.scripts.tools import cli
from amcat.models.user import User, current_user
from amcat.models.project import Project
from amcat.models.authorisation import Role, ProjectRole
from amcat.forms.fields import UserField


PROJECT_ROLE_READER=11

class AddProjectForm(forms.ModelForm):
    owner = forms.ModelChoiceField(queryset=User.objects.all(), initial=current_user().id)
    guest_role = forms.ModelChoiceField(queryset=Role.objects.filter(projectlevel=True),
                                        required=False, help_text="Leaving this value "+
                                        "empty means it will not be readable by guests.",
                                        initial=PROJECT_ROLE_READER)

    def __init__(self, *args, **kwargs):
        super(AddProjectForm, self).__init__(*args, **kwargs)
	

    class Meta:
        model = Project
	fields = ['name','description','active']


class AddProject(Script):
    """Add a project to the database."""
    
    options_form = AddProjectForm
    output_type = Project

    def run(self, _input):
	p = Project.objects.create(insert_user=current_user(), **self.options)
	
        # Add user to project (as admin)
        pr = ProjectRole(project=p, user=self.options['owner'])
        pr.role = Role.objects.get(projectlevel=True, label='admin')
        pr.save()

        return p

if __name__ == '__main__':
    cli.run_cli(AddProject)
