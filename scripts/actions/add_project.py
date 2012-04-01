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

from amcat.scripts.script import Script
from amcat.scripts.tools import cli
from amcat.models.user import User, current_user
from amcat.models.project import Project
from amcat.models.authorisation import Role, ProjectRole

PROJECT_ROLE_READER=11

class AddProjectForm(forms.ModelForm):
    owner = forms.ModelChoiceField(queryset=User.objects.all())
    guest_role = forms.ModelChoiceField(queryset=Role.objects.filter(projectlevel=True),
                                        required=False, help_text="Leaving this value "+
                                        "empty means it will not be readable by guests.",
                                        initial=PROJECT_ROLE_READER)

    @classmethod
    def get_empty(cls, user=None, **_options):
        obj = cls()
        if user is None: user = current_user()
        obj.fields['owner'].initial = user.id
        return obj

    class Meta:
        model = Project
        fields = ['name','description','active']


class AddProject(Script):
    """Add a project to the database."""

    options_form = AddProjectForm
    output_type = Project

    def run(self, _input=None):
        p = Project.objects.create(**self.options)

        # Add user to project (as admin)
        pr = ProjectRole(project=p, user=self.options['owner'])
        pr.role = Role.objects.get(projectlevel=True, label='admin')
        pr.save()

        return p

if __name__ == '__main__':
    cli.run_cli(AddProject)


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestAddProject(amcattest.PolicyTestCase):
    def test_add(self):
        u = amcattest.create_test_user()
        p = AddProject(owner=u.id, name='test', description='test').run()
        self.assertEqual(p.insert_user, current_user())
        self.assertEqual(p.owner, u)

    def test_get_form(self):
        from amcat.models.user import current_user
        u = amcattest.create_test_user()
        f = AddProject.get_empty_form()
        self.assertEqual(f.fields['owner'].initial, current_user().id)

        f = AddProject.get_empty_form(user=u)
        self.assertEqual(f.fields['owner'].initial, u.id)


