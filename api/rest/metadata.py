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
from rest_framework.metadata import SimpleMetadata

import api
import logging
from api.rest.metadata_coded_article import CODED_ARTICLE_METADATA

log = logging.getLogger(__name__)

_field_name_map = {
    "PrimaryKeyRelatedField": "ModelChoiceField",
    "ManyPrimaryKeyRelatedField": "ModelMultipleChoiceField"
}


def _get_field_name(field):
    """Return the field name to report in OPTIONS (for datatables)"""
    n = field.__class__.__name__
    return _field_name_map.get(n, n)


def _get_model_by_field(model, field_name):
    return getattr(model, field_name).get_queryset().model


class AmCATMetadata(SimpleMetadata):
    def _get_model(self, view):
        try:
            return view.queryset.model
        except AttributeError:
            return getattr(view, "model", None)

    def get_label(self, view):
        return api.rest.resources.get_resource_for_model(self._get_model(view)).get_label()

    def get_metadata_fields(self, view):
        serializer = view.get_serializer()

        for name, field in serializer.fields.items():
            field_name = None
            if hasattr(serializer, "get_metadata_field_name"):
                field_name = serializer.get_metadata_field_name(field)

            if not field_name:
                field_name = _get_field_name(field)

            yield (name, field_name)

    def determine_metadata(self, request, view):
        from api.rest.resources import get_resource_for_model
        metadata = super(AmCATMetadata, self).determine_metadata(request, view)

        if self._get_model(view) is None:
            return metadata

        metadata['label'] = self.get_label(view)

        try:
            metadata['label'] = self.get_label(view)
        except ValueError:
            log.debug("No resource for model, returning minimal metadata.")
            return metadata

        serializer = view.get_serializer()
        if hasattr(serializer, "Meta") and  hasattr(serializer.Meta, "model"):
            model = serializer.Meta.model

            metadata['models'] = {
                name: get_resource_for_model(_get_model_by_field(model, name)).get_url()
                for (name, field) in serializer.get_fields().items()
                if hasattr(field, 'queryset')
            }

        metadata['filter_fields'] = list(view.get_filter_fields())
        metadata["fields"] = dict(self.get_metadata_fields(view))
        metadata["field_list"] = [field_name for field_name, _ in self.get_metadata_fields(view)]
        return metadata

