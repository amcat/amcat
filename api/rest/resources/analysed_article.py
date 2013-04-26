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
from django.db.models import Count

from api.rest.resources.amcatresource import AmCATResource
from api.rest.serializer import AmCATModelSerializer, AmCATPaginationSerializer
from amcat.models import ArticleSet, AnalysedArticle, Plugin, Project
from rest_framework.filters import DjangoFilterBackend
from rest_framework.serializers import Serializer, SerializerMethodField
from rest_framework import fields, relations
from django_filters.filterset import FilterSet
from django_boolean_sum import BooleanSum

class AnalysedArticleSerializer(Serializer):
    def _set_narticles(self, rows):
        asets = {x["article__articlesets_set"] for x in rows}
        self._narticles =dict(ArticleSet.objects.filter(pk__in=asets).values("pk")
                                  .annotate(n=Count("articles"))
                                  .values_list("pk", "n"))

    def get_fields(self):
        flds = {f : fields.IntegerField() for f in ["articles", "done","error"]}
        flds["plugin_id"] = relations.PrimaryKeyRelatedField(queryset=Plugin.objects.all())
        flds[ "article__articlesets_set"] = relations.PrimaryKeyRelatedField(queryset=ArticleSet.objects.all())
        flds["article__articlesets_set__project"] = relations.PrimaryKeyRelatedField(queryset=Project.objects.all())
        
        return flds
    
    def convert_object(self, obj):
        if not hasattr(self, "_narticles"):
            # probably got here without serialiser, so rows are in self.object.qs
            self._set_narticles(self.object.qs)
        obj["articles"] = self._narticles.get(obj["article__articlesets_set"])
        return obj

    def field_to_native(self, obj, field_name):
        # probably got here from serialiser, so rows are in object_list
        self._set_narticles(obj.object_list)
        return super(AnalysedArticleSerializer, self).field_to_native(obj, field_name)
    
    def to_native(self, obj):
        # prevent unpacking of iterable dict
        if type(obj) == dict:
            return self.convert_object(obj)
        return super(AnalysedArticleSerializer, self).to_native(obj)

class AnalysedArticlesPaginationSerializer(AmCATPaginationSerializer):
    class Meta:
        object_serializer_class = AnalysedArticleSerializer

class AnalysedArticleResource(AmCATResource):
    model = AnalysedArticle
    extra_filters = ["article__articlesets_set__id", "article__articlesets_set__project__id"]

    use_distinct = False
    serializer_class = AnalysedArticleSerializer
    pagination_serializer_class = AnalysedArticlesPaginationSerializer

    def get_queryset(self, *args, **kargs):
        qs = (super(AnalysedArticleResource, self).get_queryset(*args, **kargs)
              .values("article__articlesets_set__project", "plugin_id", "article__articlesets_set")
              .annotate(assigned=Count("id"), done=BooleanSum("done"), error=BooleanSum("error"))
              )
        return qs
