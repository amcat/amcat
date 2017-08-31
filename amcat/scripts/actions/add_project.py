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

import logging

from django import forms

from amcat.forms.fields import StaticModelChoiceField
from amcat.models.authorisation import ProjectRole, Role
from amcat.models.project import Project
from amcat.models.user import User
from amcat.scripts.script import Script

log = logging.getLogger(__name__)
PROJECT_ROLE_READER=11

class AddProjectForm(forms.ModelForm):
    owner = forms.ModelChoiceField(queryset=User.objects.all())
    guest_role = forms.ModelChoiceField(queryset=Role.objects.all(),
                                        required=False, help_text="Leaving this value "+
                                        "empty means it will not be readable by guests.",
                                       initial=PROJECT_ROLE_READER)
    insert_user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)

    @classmethod
    def get_empty(cls, user=None, **_options):
        obj = cls()
        try:
            for field in ("owner", "insert_user"):
                obj.fields[field].initial = user.id
                obj.fields[field].queryset = User.objects.filter(id=user.id)
                obj.fields[field].widget = forms.HiddenInput()
        except AttributeError: #no user
            pass

        return obj

    class Meta:
        model = Project
        fields = ['name','description','active']


class AddProject(Script):
    """Add a project to the database.

    Guest role specifies the 'default' role that anybody has, so if you choose 'Reader' everyone can see the contents of your project.
    If you are not allowed to share the texts (e.g. for copyright reasons), choose 'Metareader'.
    To create a private project, select '----' as guest role.
    """

    options_form = AddProjectForm
    output_type = Project

    def run(self, _input=None):
        p = Project.objects.create(**self.options)
        # Add user to project (as admin)
        pr = ProjectRole(project=p, user=self.options['owner'])
        pr.role = Role.objects.get(label='admin')
        pr.save()
        # Make project favourite for creating user
        self.options['owner'].userprofile.favourite_projects.add(p)

        return p

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli()

