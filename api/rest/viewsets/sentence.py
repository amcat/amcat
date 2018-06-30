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
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import Sentence
from amcat.tools import sbd
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin

__all__ = ("SentenceSerializer", "SentenceViewSetMixin", "SentenceViewSet")

class SentenceSerializer(AmCATModelSerializer):
    class Meta:
        model = Sentence
        fields = '__all__'

class SentenceViewSetMixin(AmCATViewSetMixin):
    serializer_class = SentenceSerializer
    model_key = "sentence"
    model = Sentence

class SentenceViewSet(SentenceViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Sentence

    def filter_queryset(self, queryset):
        qs = super(SentenceViewSet, self).filter_queryset(queryset)
        return qs.filter(article=self.article, id__in=sbd.get_or_create_sentences(self.article))
