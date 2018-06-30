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

from amcat.models import Codebook, CodingSchema, Language
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets import CodingJobViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin

log = logging.getLogger(__name__)

__all__ = ("CodebookSerializer", "CodebookViewSetMixin", "CodingJobCodebookViewSet",
            "CodebookViewSet", "CodebookLanguageViewSet")

def serialize_codebook_code(codebook, ccode):
    return {
        "codebookcode" : ccode.id,
        "code" : ccode.code_id,
        "parent" : ccode.parent_id,
        "hide" : ccode.hide,
        "valid_from" : ccode.validfrom,
        "valid_to" : ccode.validto,
        "ordernr" : ccode.ordernr,
        "labels" : codebook._labels[ccode.code_id],
        "label": ccode.code.label,
    }

class CodebookSerializer(AmCATModelSerializer):
    codes = serializers.SerializerMethodField()
    
    class Meta:
        model = Codebook
        fields = '__all__'

    def get_codes(self, codebook):
        # Hack: we pass `codebook` to serialize_codebook_code, so it can use codebook's
        # internal label cache, which is way faster than iterating over all codebookcodes
        # and requesting their labels.
        codebook.cache()
        codebook.cache_labels()
        return (serialize_codebook_code(codebook, ccode) for ccode in codebook.codebookcodes)
        

class CodebookViewSetMixin(AmCATViewSetMixin):
    queryset = Codebook.objects.all()
    model_key = "codebook"
    model = Codebook
    search_fields = ("id", "project__name", "name")

class CodebookViewSet(ProjectViewSetMixin, CodebookViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Codebook
    queryset = Codebook.objects.all()
    serializer_class = CodebookSerializer

    def filter_queryset(self, queryset):
        qs = super(CodebookViewSet, self).filter_queryset(queryset)
        return qs.filter(Q(project=self.project)|Q(projects_set=self.project)).distinct()

class LanguageSerializer(AmCATModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'

class LanguageViewSetMixin(AmCATViewSetMixin):
    model_key = "language"
    model = Language

class CodebookLanguageViewSet(ProjectViewSetMixin, CodebookViewSetMixin,
                              LanguageViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Language
    serializer_class = LanguageSerializer
    queryset = Language.objects.all()

    def filter_queryset(self, queryset):
        return Language.objects.filter(id__in=self.codebook.get_language_ids())

class CodingJobCodebookViewSet(ProjectViewSetMixin, CodingJobViewSetMixin,
                      CodebookViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Codebook
    serializer_class = CodebookSerializer
    queryset = Codebook.objects.all()

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




