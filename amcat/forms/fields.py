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
Replacement for Django Forms.forms fields module. This module contains all
standard forms and more.
"""
import csv

from amcat.models.user import User
from django import forms
from django.forms import fields
from django.db import models
from django.core.exceptions import ValidationError 

import logging; log = logging.getLogger()

__all__ = ['JSONField', 'UserField', 'CSVField']

class JSONField(models.TextField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs.update(dict(default='{}'))
        super(JSONField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, basestring):
            return json.loads(value)
        return value

    def get_prep_value(self, value):
        return json.dumps(value)


class UserField(forms.SlugField):
    default_error_messages = {
        'exists' : 'This username is not available.'
    }

    def validate(self, value):
        super(UserField, self).validate(value)

        try:
            User.objects.get(username=value)
        except User.DoesNotExist:
            pass
        else:
            raise ValidationError(self.default_error_messages['exists'])



class CSVField(forms.FileField):
    default_error_messages = {
        'notcsv' : 'The uploaded file is corrupt or not valid.',
        'columnerr' : ' The value (%s) at row %s, column %s is not valid. Validator reported: %s',
        'no_such_column' : 'Column "%s" is required, but not found in "%s"',
        'delimiter' : 'Delimiter must be a one-character ASCII value.'
    }

    def __init__(self, columns=None, delimiter=",", *args, **kwargs):
        """
        A FileField for CSVFiles.

        @type columns: dictionary
        @param columns: this dictionary contains the names and forms of the
        columns to be specified in the CSV file. For example:

        csv = CSVField({
            'name' : forms.CharField(max_length=30),
            'active' : forms.BooleanField()
        })
        """
        self._columns = columns or dict()
        self.delimiter = delimiter

        super(CSVField, self).__init__(*args, **kwargs)

    def set_delimiter(self, delimiter):
        self.delimiter = delimiter

    def _to_python(self, data):
        data = super(CSVField, self).to_python(data)

        try:
            str(self.delimiter)
            assert(len(self.delimiter) == 1)
        except TypeError:
            raise ValidationError(self.error_messages['delimiter'])

        # Check if csv file is valid
        try:
            cfile = csv.reader(data, delimiter=str(self.delimiter))
            columns = [c.lower() for c in cfile.next()]
        except Exception as e:
            log.exception(e)
            raise ValidationError(self.error_messages['notcsv'])

        # Check for column existence
        for col, field in self._columns.items():
            if col not in columns and field.required:
                raise ValidationError(self.error_messages['no_such_column'] % (col, data.file_name))

        # Check every cell and yield a dictionary (column : value)
        for rownr, row in enumerate(cfile):
            _row = []
            for colnr, val in enumerate(row):
                field = self._columns.get(columns[colnr], None)
                if field is not None:
                    try:
                        val = field.clean(val)
                    except ValidationError as e:
                        raise ValidationError(self.error_messages['columnerr'] % (val, rownr+1, columns[colnr], e.messages[0]))

                _row.append(val)

            yield dict(zip(columns, _row))

    def to_python(self, data):
        return list(self._to_python(data))
