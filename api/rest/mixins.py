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
from django.db.models.fields.related import RelatedField, ForeignObjectRel


def get_related_fieldname(model, fieldname):
    field = model._meta.get_field(fieldname)

    if isinstance(field, (ForeignObjectRel, RelatedField)):
        return "{}__id".format(fieldname)

    return fieldname


class ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class AmCATFilterMixin(object):
    """
    Set the correct fields for filtering
    """
    extra_filters = []
    ignore_filters = ['auth_token__id']

    @classmethod
    def _get_filter_fields_for_model(cls):
        for field in cls.queryset.model._meta.get_fields():
            fieldname = field.name
            fieldname = get_related_fieldname(cls.queryset.model, fieldname)
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


class DatatablesMixin(AmCATFilterMixin):
    pass

