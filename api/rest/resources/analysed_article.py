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
from api.rest.serializer import AmCATModelSerializer
from amcat.models import ArticleSet, AnalysedArticle
from rest_framework.filters import DjangoFilterBackend
from rest_framework.serializers import Serializer
from django_filters.filterset import FilterSet

class AnalysedArticleResource(AmCATResource):
    model = AnalysedArticle
    extra_filters = ["article__articlesets_set__id", "article__articlesets_set__project__id"]

    paginate_by = None
    paginate_by_param = None
    
    class serializer_class(Serializer):
        def convert_object(self, obj):
            return obj

    def get_queryset(self, *args, **kargs):
        qs = super(AnalysedArticleResource, self).get_queryset(*args, **kargs)
        print(qs.query)
        qs = qs.values("article__articlesets_set__project", "plugin_id", "done","error", "article__articlesets_set").annotate(n=Count("id")) 
        return qs

    # avoid AmCAT filter backend because annotate and distinct don't go together very well
    # could also add a distinct flag on the backend I guess
    
    class filter_backend(DjangoFilterBackend):
        def get_filter_class(self, view):
            class AnalysedArticleFilterClass(FilterSet):
                class Meta:
                    model = view.model
                    fields = tuple(view.get_filter_fields())
                    print ">>>>>", fields


            return AnalysedArticleFilterClass
