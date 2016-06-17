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
from functools import wraps
from typing import Container

from django import forms
from django.core.exceptions import ValidationError
from exportable.columns import Column

ASC = "+"
DESC = "-"


def wrap(func):
    def my_decorator(wrapped_function):
        @wraps(wrapped_function)
        def wrapper(*args, **kwds):
            return func(wrapped_function(*args, **kwds))
        return wrapper
    return my_decorator


class ColumnListField(forms.CharField):
    def __init__(self, columns: Container[Column] = (), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.columns = columns

    @wrap(list)
    def to_python(self, value):
        if value is None:
            return []

        label_map = {c.label: c for c in self.columns}

        for label in value.split(","):
            try:
                yield label_map[label]
            except KeyError:
                raise ValidationError("Column with label '{}' not found in: {}".format(label, self.columns))


class OrderingField(forms.CharField):
    def __init__(self, columns: Container[Column]=(), orderable: Container[Column]=(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.columns = columns
        self.orderable = orderable

    @wrap(list)
    def to_python(self, value):
        if value is None:
            return []

        label_map = {c.label: c for c in self.columns}
        orderable = {c.label: c for c in self.orderable}

        for label in value.split(","):
            try:
                if label.startswith(DESC):
                    dir, column = DESC, label_map[label[1:]]
                if label.startswith(ASC):
                    dir, column = ASC, label_map[label[1:]]
                else:
                    # Assume ascending (+) as default order
                    dir, column = ASC, label_map[label]
            except KeyError:
                raise ValidationError("Column with label '{}' not found in: {}".format(label, self.columns))
            else:
                if column not in orderable:
                    raise ValidationError("Column with label '{}' not orderable. Options: {}".format(label, self.orderable))
                else:
                    yield dir, column