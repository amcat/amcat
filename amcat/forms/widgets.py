# ##########################################################################
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

from django import forms

__all__ = ["BootstrapSelect", "BootstrapMultipleSelect"]


class BootstrapSelect(forms.widgets.Select):
    def _build_attrs(self, attrs=None, **kwargs):
        attrs = dict() if attrs is None else attrs
        attrs.update(kwargs)
        return attrs

    def render(self, name, value, attrs=None, **kwargs):
        attrs = self._build_attrs(attrs, **{'class': 'multiselect'})
        return super(BootstrapSelect, self).render(name, value, attrs=attrs)


class BootstrapMultipleSelect(BootstrapSelect, forms.widgets.SelectMultiple):
    def render(self, name, value, attrs=None, **kwargs):
        attrs = self._build_attrs(attrs, multiple='multiple')
        return super(BootstrapMultipleSelect, self).render(name, value, attrs=attrs)

def _convert_widget(widget):
    if isinstance(widget, forms.widgets.SelectMultiple):
        return BootstrapMultipleSelect(attrs=widget.attrs, choices=widget.choices)

    if isinstance(widget, forms.widgets.Select):
        return BootstrapSelect(attrs=widget.attrs, choices=widget.choices)

    return widget


def convert_to_bootstrap_select(form):
    for field in form.fields:
        form.fields[field].widget = _convert_widget(form.fields[field].widget)

def add_bootstrap_classes(field: forms.Field):
    classlist = [x for x in (field.widget.attrs.get('class'),) if x is not None]
    classlist += ["form-control"]
    field.widget.attrs['class'] = " ".join(classlist)
    return field
