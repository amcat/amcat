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


from django import forms

from django.contrib.auth.models import User

from amcat.forms import forms

from django.contrib.auth.forms import PasswordResetForm

class UserPasswordResetForm(PasswordResetForm):
    """
    Reset Password by filling in either email address or user name.

    If email is valid, choose the email address.
    Otherwise, if the username is recognize find the matching email.
    Send the user a password reset message (super class function).
    """
    username = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(UserPasswordResetForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['placeholder'] = 'Email'
        self.fields['username'].widget.attrs['placeholder'] = 'Username'
        self.users_cache = None

    def clean(self):
        cleaned_data = super(UserPasswordResetForm, self).clean()
        email = cleaned_data.get("email")
        username = cleaned_data.get("username")
        usererror = self._errors.get("username")
        if usererror:
            del self._errors["username"]
        if email:
            return self.cleaned_data
        if username:
            self.users_cache = User.objects.filter(username=username)
            if  len(self.users_cache) == 0:
                print "Add unknown user error\n"
                msg = u"User unknown"
                self._errors["username"] = self.error_class([msg])
                print "EEE:", self._errors.get("username")
            else:
                emailerror = self._errors.get("email")
                if emailerror:
                    del self._errors["email"]
                    cleaned_data["email"] = self.users_cache[0]
                else:
                    print "UNEXPECTED not error email"
                print repr(self.users_cache[0].email)
        return self.cleaned_data

