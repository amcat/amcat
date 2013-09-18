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

from django.forms import *
from django.forms.widgets import HiddenInput
from django.forms.util import ErrorList

from operator import attrgetter, itemgetter

def _remove_duplicates(seq):
    """Remove duplicates in `seq` whilst preserving order."""
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

def order_fields(fields=(), classes=()):
    """
    Decorator to order fields on based on creation_counter attribute. To
    force another ordering, pass a list of fields. This mimicks the intended
    behaviour of Django (according to the docs):

      > for each field in the form (in the order they are declared in the
      > form definition
      ..
      > These methods are run in the order given above, one field at a
      > time. That is, for each field in the form (in the order they
      > are declared in the form definition), the Field.clean() method
      > (or its override) is run, then clean_().

    Relevant links:
     - http://stackoverflow.com/a/3299585
     - http://docs.djangoproject.com/en/dev/ref/forms/validation/

    Implementation credits:
     - http://stackoverflow.com/a/8476642
     - http://stackoverflow.com/a/2619586

    @type fields: iterable of strings
    @param fields: these fields will come first, regardless of `creation_counter`

    @type classes: iterable of Form classes
    @param classes: classes to consider when ordering fields. It should
                     only include subclasses.
    """
    def decorator(form):
        original_init = form.__init__

        def init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)        

            # keyOrder will be a list with the fields of each class sorted
            keyOrder = []
            for cls in classes + (self.__class__,):
                # Sort according to creation_counter
                keyOrder += [field[0] for field in sorted(
                    cls.base_fields.iteritems(), key=(
                        lambda f : f[1].creation_counter
                    )
                )]

            self.fields.keyOrder = _remove_duplicates(keyOrder)

            # Force ordering of passed fields
            for field in fields[::-1]:
                self.fields.insert(0, field, self.fields.pop(field))

        form.__init__ = init
        return form            
    return decorator

class HideFieldsForm(ModelForm):
    """
    This form takes an extra parameter upon initilisation `hide`, which
    indicates which fields need to be hidden. This allows developers to
    disable editing for some of its fields, which can be benificial when
    values are already known (e.g. for existing database entries).
    """
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
            initial=None, error_class=ErrorList, label_suffix=':',
            empty_permitted=False, instance=None, hidden=None):
        """
        @param hidden: fields to be hidden
        @type hidden: iterable or string (for single field)
        """
        # *sigh*..
        super(HideFieldsForm, self).__init__(
            data=data, files=files, auto_id=auto_id, prefix=prefix,
            initial=initial, error_class=error_class, instance=instance,
            label_suffix=label_suffix, empty_permitted=empty_permitted
        )

        if isinstance(hidden, str):
            # Make sure hidden is a iterable
            hidden = (hidden,)
        elif hidden is None:
            return

        for field_name in hidden:
            del self.fields[field_name]

