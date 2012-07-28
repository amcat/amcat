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
This module provides form base classes, to provide extra functionality on top
of the default behaviour of Django Forms.
"""

from django import forms
from django.forms.widgets import HiddenInput
from django.forms.util import ErrorList

class HideFieldsForm(forms.ModelForm):
    """
    This form takes an extra parameter upon initilisation `hide`, which
    indicates which fields need to be hidden. This allows developers to
    disable editing for some of its fields, which can be benificial when
    values are already known (e.g. for existing database entries).
    """
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
            initial=None, error_class=ErrorList, label_suffix=':',
            empty_permitted=False, instance=None, hidden=tuple()):
        """
        @param hidden: fields to be hidden
        @type hidden: iterable
        """
        # *sigh*..
        super(HideFieldsForm, self).__init__(
            data=data, files=files, auto_id=auto_id, prefix=prefix,
            initial=initial, error_class=error_class, instance=instance,
            label_suffix=label_suffix, empty_permitted=empty_permitted
        )

        for field_name in fields:
            self.fields[field_name].widget = HiddenInput()

