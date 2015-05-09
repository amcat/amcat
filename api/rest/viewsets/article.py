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
from django.forms import ModelChoiceField

from rest_framework.fields import ModelField, CharField
from rest_framework.viewsets import ModelViewSet

from amcat.models import Medium, Project
from amcat.tools.amcates import ES
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from amcat.models import Article, ArticleSet, ROLE_PROJECT_READER
from api.rest.viewsets.project import CannotEditLinkedResource, NotFoundInProject

__all__ = ("ArticleSerializer", "ArticleViewSet")
import logging
log = logging.getLogger(__name__)

class ArticleViewSetMixin(AmCATViewSetMixin):
    queryset = Article.objects.all()
    model_key = "article"
    model = Article


class MediumField(ModelField):
    def to_internal_value(self, data):
        try:
            int(data)
        except ValueError:
            return Medium.get_or_create(data)
        else:
            return super(MediumField, self).to_internal_value(data)

    def to_representation(self, obj):
        return obj.medium_id


class ArticleSerializer(AmCATModelSerializer):
    project = ModelChoiceField(queryset=Project.objects.all(), required=True)
    medium = MediumField(ModelChoiceField(queryset=Medium.objects.all()))
    uuid = CharField(read_only=False, required=False)

    def validate(self, attrs):
        validated_data = super(ArticleSerializer, self).validate(attrs)
        validated_data["project"] = self.context["view"].project
        return validated_data

    def create(self, validated_data):
        try:
            article = Article.objects.get(uuid=validated_data["uuid"])
        except (Article.DoesNotExist, KeyError) as e:
            article = super(ArticleSerializer, self).create(validated_data)

        elastic = ES()
        elastic.add_articles([article.id])
        elastic.flush()

        self.context["view"].articleset.add_articles([article])
        return article

    class Meta:
        model = Article
        read_only_fields = ('id', 'project', 'length', 'insertdate', 'insertscript')


class ArticleViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, ArticleViewSetMixin, DatatablesMixin, ModelViewSet):
    model = Article
    model_key = "article"
    permission_map = {'GET': ROLE_PROJECT_READER}
    serializer_class = ArticleSerializer
    queryset = Article.objects.all()
    http_method_names = ("get", "post")

    def check_permissions(self, request):
        # make sure that the requested set is available in the projec, raise 404 otherwiset
        # sets linked_set to indicate whether the current set is owned by the project
        if self.articleset.project == self.project:
            pass
        elif self.project.articlesets.filter(pk=self.articleset.id).exists():
            if request.method == 'POST':
                raise CannotEditLinkedResource()
        else:
            raise NotFoundInProject()
        return super(ArticleViewSet, self).check_permissions(request)

    @property
    @cached
    def articleset(self):
        articleset_id = int(self.kwargs['articleset'])
        return ArticleSet.objects.get(pk=articleset_id)

    def filter_queryset(self, queryset):
        queryset = super(ArticleViewSet, self).filter_queryset(queryset)
        return queryset.filter(articlesets_set=self.articleset)
