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
Script add a user to db and users table
"""

import logging; log = logging.getLogger(__name__)

from django import forms

#from amcat.tools import dbtoolkit
from amcat.tools.djangotoolkit import get_or_create
from amcat.scripts.script import Script
from amcat.models.user import User, Affiliation, create_user
from amcat.models.authorisation import Role
from amcat.forms.fields import UserField

class AddUserForm(forms.ModelForm):
    username = UserField()
    password = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

class AddUser(Script):
    """Add a user to the database. A new DB user will be created,
    and the user will be added to the users table.

    If the user already exists in the database but not in the users table,
    he/she will be added to that table.
    """

    options_form = AddUserForm
    output_type = User

    def _validate_form(self):
        # If affiliation is given as a string, get or create the affiliation
        aff = self.bound_form.data['affiliation']
        if isinstance(aff, basestring):
            self.bound_form.data['affiliation'] = get_or_create(Affiliation, name=aff).id
        role = self.bound_form.data['role']
        if isinstance(role, basestring):
            self.bound_form.data['role'] = Role.objects.get(label=role, projectlevel=False).id

        super(AddUser, self)._validate_form()

    def run(self, _input):
        u = create_user(insert_if_db_user_exists=True, **self.options)
        if u.password:
            log.info("Created new database user %r with password=%r" % (u.username, u.password))
        else:
            log.info("Created User object for database user %r" % (u.username))
        return u

if __name__ == '__main__':
    from amcat.scripts.tools import cli
    cli.run_cli(AddUser)
