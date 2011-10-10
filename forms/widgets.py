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
Replacement for the standard Django forms.widgets module. It contains all
standard widgets plus extra (amcat-specific) widgets.
"""

from django.forms.widgets import *
from django.forms import widgets

__ALL__ = list(widgets.__ALL__) + ["JQuerySelect", "JQueryMultipleSelect"]

class JQuerySelect(widgets.Select):
    def _build_attrs(attrs=None, **kwargs):
        attrs = dict() if attrs is None else attrs
        attrs.update(kwargs)
        return attrs

    def render(self, attrs=None, *args, **kwargs):
        attrs = self._build_attrs(attrs, **{'class' : 'multiselect'})
        return super(JQuerySelect, self).render(*args, attrs=attrs, **kwargs)
     
class JQueryMultipleSelect(JQuerySelect):
    def render(self, attrs=None, *args, **kwargs):
        attrs = self._build_attrs(attrs, multiple='multiple')
        return super(JQueryMultipleSelect, self).render(*args, attrs=attrs, **kwargs)
