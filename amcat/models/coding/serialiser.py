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
(De)Serialisation support for coding values

Coding Values need to be serialised and deserialised based on the
schema field that they are an coding of.

Definitions:
Serialised Value: a primitive type (currently: str or int)
Deserialised Value: a domain object, possibly a django Model instance

"""

import logging

log = logging.getLogger(__name__)

from amcat.models.coding.code import Code
from amcat.models.coding.codebook import Codebook
from django import forms
import functools


class BaseSerialiser(object):
    """Base class for serialisation support for schema fields"""

    def __init__(self, field, deserialised_type=str, serialised_type=str):
        self.field = field
        self.deserialised_type = deserialised_type
        self.serialised_type = serialised_type

    def deserialise(self, value):
        """Convert the given serialised value to a domain object

        @param value: The value to be deserialized, which should be of type self.serialized_type
        @return: a value of type self.deserialized_Type. Raises an error if value could not
                 be deserialized
        """
        if value is None: return None
        return self.deserialised_type(value)

    def serialise(self, value):
        """Convert the given domain object to a serialised value

        @param value: The value to be serialized, which should be of type self.deserialized_type
        @return: a value of type self.serialized_Type. Raises an error if value could not
                 be serialized
        """
        if value is None: return None
        return self.serialised_type(value)

    @property
    def possible_values(self):
        """Get the possible values

        @return: a sequence of (deserialised) values
                 or None if this serialiser in not for a 'drop down' field
        """
        return None

    def value_label(self, value):
        """Get a label for the given (deserialised) value"""
        return str(value)

    def get_export_fields(self):
        """Return a sequence of (id, django form fields) pairs with export options for this field
        The id and field label need only be locally unique, they will be prepended with the field name
        """
        return []

    def get_export_columns(self, **options):
        """
        Return (label, function) pair for each column that a codingjob export should include.
        The function will be called with the serialised coded value as the only argument.
        The label need only be locally unique, it will be prepended with the field name.
        @param **options: the form values of the fields specified by get_export_fields
        """
        yield "", self.deserialise


class TextSerialiser(BaseSerialiser):
    """Simple str - str serialiser"""

    def __init__(self, field):
        super(TextSerialiser, self).__init__(field, str, str)


class IntSerialiser(BaseSerialiser):
    """Simple int - int serialiser"""

    def __init__(self, field):
        super(IntSerialiser, self).__init__(field, int, int)


class BooleanSerialiser(BaseSerialiser):
    """Boolean serialiser with 'possible values'"""

    def __init__(self, field):
        super(BooleanSerialiser, self).__init__(self, bool, int)

    @property
    def possible_values(self):
        return [True, False]


class QualitySerialiser(BaseSerialiser):
    """Boolean serialiser with 'possible values'"""

    def __init__(self, field):
        super(QualitySerialiser, self).__init__(self, int, int)

    @property
    def possible_values(self):
        return range(-10, 15, 5)  # 15 because end point is ommitted

    def value_label(self, value):
        if value == 0: return "0"
        if value is None: return value
        return "%+1.1f" % (value / 10.)

    def get_export_columns(self, **options):
        yield "", self.value_label


class IntervalSerialiser(BaseSerialiser):
    """Stub for interval serialiser"""

    def __init__(self, field):
        super(IntervalSerialiser, self).__init__(field, int, int)


_memo = {}


def CodebookSerialiser(field):
    """Retrieve/Create a memoized codebooksereialiser for the given field.codebook"""
    # no harm if threads access concurrently, so no need to use local store or mutex
    # limited total no of codebooks, so no harm in memoising all of them
    # or should we memoise on codebook level, ie have a general codebook factory?
    codebookid = field.codebook_id
    try:
        return _memo[codebookid]
    except KeyError:
        _memo[codebookid] = _CodebookSerialiser(field)
        return _memo[codebookid]


class _CodebookSerialiser(BaseSerialiser):
    """int - amcat.models.coding.Code serialiser"""

    def __init__(self, field):
        super(_CodebookSerialiser, self).__init__(field, Code, int)

    @property
    def codebook(self):
        try:
            return self._codebook
        except AttributeError:
            self._codebook = list(Codebook.objects.filter(pk=self.field.codebook_id)
                                  .prefetch_related("codebookcode_set"))[0]
            return self._codebook

    def deserialise(self, value):
        try:
            return self.codebook.get_code(value)
        except Code.DoesNotExist:
            # code was removed from codebook
            return Code.objects.get(pk=value)

    def serialise(self, value):
        if value is None: return None
        return value.id

    @property
    def possible_values(self):
        return self.field.codebook.codes

    def value_label(self, value):
        #self.field.codebook.cache_labels(language)
        return value.label

    def get_export_fields(self):
        yield "ids", forms.BooleanField(initial=True, label="ids", required=False)
        yield "labels", forms.BooleanField(initial=True, label="labels", required=False)
        yield "parents", forms.IntegerField(initial=0, required=False, label="# parents")

    def _get_ancestor(self, value, i, label=False):
        try:
            ancestors = list(self.field.codebook.get_ancestor_ids(value))
        except (KeyError, ValueError):
            log.exception("Error on getting ancestors for {value}".format(**locals()))
            return None
        ancestor_id = ancestors[max(0, len(ancestors) - i - 1)]
        return self.value_label(self.deserialise(ancestor_id)) if label else ancestor_id

    def get_export_columns(self, ids, labels, parents, **options):
        if parents:
            for i in range(parents):
                if ids:
                    yield "_parent_{i}_id".format(**locals()), functools.partial(self._get_ancestor, i=i)
                if labels:
                    yield "_parent_{i}_label".format(**locals()), functools.partial(self._get_ancestor, i=i, label=True)
        if ids:
            yield " (id)", lambda x: x
        if labels:
            yield "", lambda x: self.value_label(self.deserialise(x))
