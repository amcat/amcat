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
import logging
from django.db.models import Q

from rest_framework import serializers
from rest_framework.viewsets import ReadOnlyModelViewSet

from amcat.models import Codebook, CodingSchema
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets import CodingJobViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin

log = logging.getLogger(__name__)

__all__ = ("CodebookSerializer", "CodebookViewSetMixin", "CodingJobCodebookViewSet",
            "CodebookViewSet")

def serialize_codebook_code(codebook, ccode):
    function = ccode.function

    return {
        "codebookcode" : ccode.id,
        "code" : ccode.code_id,
        "parent" : ccode.parent_id,
        "hide" : ccode.hide,
        "valid_from" : ccode.validfrom,
        "valid_to" : ccode.validto,
        "ordernr" : ccode.ordernr,
        "labels" : codebook._labels[ccode.code_id],
        "function" : {
            "id" : function.id,
            "label" : function.label,
            "description" : function.description
        }
    }

class CodebookSerializer(AmCATModelSerializer):
    model = Codebook
    codes = serializers.SerializerMethodField('get_codes')

    def get_codes(self, codebook):
        # Hack: we pass `codebook` to serialize_codebook_code, so it can use codebook's
        # internal label cache, which is way faster than iterating over all codebookcodes
        # and requesting their labels.
        codebook.cache(select_related=("function",))
        codebook.cache_labels()
        return (serialize_codebook_code(codebook, ccode) for ccode in codebook.codebookcodes)

class CodebookViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodebookSerializer
    model_key = "codebook"
    model = Codebook
    search_fields = ("id", "project__name", "name")

class CodebookViewSet(ProjectViewSetMixin, CodebookViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Codebook

    def filter_queryset(self, queryset):
        qs = super(CodebookViewSet, self).filter_queryset(queryset)
        return qs.filter(Q(project=self.project)|Q(projects_set=self.project))

class CodingJobCodebookViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                      CodebookViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Codebook
    model_serializer_class = CodebookSerializer

    def _get_codebook_ids(self):
        """
        Get codebook ids based on the current codingjob. Selects all highlighters, and
        all codebooks of codingschemafields of codingschemas belonging to the job.
        """
        codingschema_ids = (self.codingjob.articleschema_id, self.codingjob.unitschema_id)
        codingschemas = (CodingSchema.objects.only("id").filter(id__in=codingschema_ids)
                         .prefetch_related("highlighters", "fields"))

        for codingschema in codingschemas:
            for highlighter in codingschema.highlighters.all():
                yield highlighter.id
            for field in codingschema.fields.all():
                yield field.codebook_id

    def filter_queryset(self, queryset):
        qs = super(CodingJobCodebookViewSet, self).filter_queryset(queryset)
        return qs.filter(id__in=set(self._get_codebook_ids()) - {None,}).distinct()




