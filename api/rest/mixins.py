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
import api.rest

from django.db.models.fields.related import RelatedField
from django.db.models.related import RelatedObject


def get_related_fieldname(model, fieldname):
    field = model._meta.get_field_by_name(fieldname)[0]

    if isinstance(field, (RelatedObject, RelatedField)):
        return "{}__id".format(fieldname)

    return fieldname


class ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


_field_name_map = {
    "PrimaryKeyRelatedField": "ModelChoiceField",
    "ManyPrimaryKeyRelatedField": "ModelMultipleChoiceField"
}


def _get_field_name(field):
    """Return the field name to report in OPTIONS (for datatables)"""
    n = field.__class__.__name__
    return _field_name_map.get(n, n)

class AmCATMetadataMixin(object):
    """Give the correct metadata for datatables"""

    @classmethod
    def get_label(cls):
        return '{{{label}}}'.format(
            label=getattr(cls.model, '__label__', 'label')
        )

    def get_metadata_fields(self):
        serializer = self.get_serializer()
        for name, field in serializer.get_fields().iteritems():
            field_name = None
            if hasattr(serializer, "get_metadata_field_name"):
                field_name = serializer.get_metadata_field_name(field)

            if not field_name:
                field_name = _get_field_name(field)

            yield (name, field_name)

    def metadata(self, request):
        """This is used by the OPTIONS request; add models, fields, and label for datatables"""
        metadata = super(AmCATMetadataMixin, self).metadata(request)
        metadata['label'] = self.get_label()
        grfm = api.rest.resources.get_resource_for_model

        serializer = self.get_serializer()
        metadata['models'] = {name: grfm(field.queryset.model).get_url()
                              for (name, field) in serializer.get_fields().iteritems()
                              if hasattr(field, 'queryset')}

        metadata["fields"] = dict(self.get_metadata_fields())
        metadata['filter_fields'] = list(self.get_filter_fields())

        return metadata


class AmCATFilterMixin(object):
    """
    Set the correct fields for filtering
    """
    extra_filters = []
    ignore_filters = ['auth_token__id']

    @classmethod
    def _get_filter_fields_for_model(cls):
        for fieldname in cls.model._meta.get_all_field_names():
            fieldname = get_related_fieldname(cls.model, fieldname)
            if fieldname in cls.ignore_filters:
                continue
            yield fieldname

    @classmethod
    def get_filter_fields(cls):
        """Return a list of fields that will be used to filter on"""
        result = ['pk']
        for field in cls._get_filter_fields_for_model():
            result.append(field)
        for field in cls.extra_filters:
            result.append(field)
        return result

    filter_fields = ClassProperty(get_filter_fields)


class DatatablesMixin(AmCATFilterMixin, AmCATMetadataMixin):
    pass


