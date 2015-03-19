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
from django.db.models import Count, Q
from rest_framework import serializers
from amcat.models.coding.codingjob import CodingJob
from amcat.models.article import Article
from amcat.models.sentence import  Sentence
from amcat.models.coding.codebook import Codebook
from amcat.models.coding.codingrule import CodingRule
from amcat.models.coding.codingschemafield import CodingSchemaField
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models.coding.codedarticle import STATUS_COMPLETE, STATUS_IRRELEVANT, CodedArticle, STATUS_INPROGRESS, STATUS_NOTSTARTED
from amcat.tools import sbd
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingschemafield import CodingSchemaFieldViewSetMixin, CodingSchemaFieldSerializer
from api.rest.viewsets.coding.codingrule import CodingRuleViewSetMixin, CodingRuleSerializer
from api.rest.viewsets.sentence import SentenceViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin

STATUS_DONE = (STATUS_COMPLETE, STATUS_IRRELEVANT)
STATUS_TODO = (STATUS_INPROGRESS, STATUS_NOTSTARTED)

__all__ = ("CodingJobViewSetMixin", "CodingJobSerializer", "CodingJobViewSet",
           "CodingJobArticleViewSet", "CodingJobArticleSentenceViewSet",
           "CodingJobHighlighterViewSet", "CodingJobCodingRuleViewSet",
           "CodingJobCodingSchemaFieldViewSet")

class CodingJobSerializer(AmCATModelSerializer):
    """
    This serializer for codingjob includes the amount of total jobs
    and done jobs. Because it would be wholly inefficient to calculate
    the values per codingjob, we ask the database to aggregate for us
    in one query.
    """
    articles = serializers.SerializerMethodField('get_n_articles')
    complete = serializers.SerializerMethodField('get_n_done_jobs')
    todo = serializers.SerializerMethodField('get_n_todo_jobs')

    def _get_codingjobs(self):
        view = self.context["view"]
        if hasattr(view, "object_list"):
            return view.object_list.distinct()
        return CodingJob.objects.filter(id=view.object.id)

    def _get_coded_articles(self):
        return CodedArticle.objects.filter(codingjob__in=self._get_codingjobs())

    @cached
    def _get_n_done_jobs(self):
        return dict(self._get_coded_articles().filter(status__id__in=STATUS_DONE)
                    .values("codingjob").annotate(n=Count("codingjob"))
                    .values_list("codingjob__id", "n"))

    @cached
    def _get_n_todo_jobs(self):
        return dict(self._get_coded_articles().filter(status__id__in=STATUS_TODO)
                    .values("codingjob").annotate(n=Count("codingjob"))
                    .values_list("codingjob__id", "n"))

    @cached
    def _get_n_articles(self):
        return dict(self._get_codingjobs().annotate(n=Count("articleset__articles")).values_list("id", "n"))

    def get_n_articles(self, obj):
        if not obj: return 0
        return self._get_n_articles().get(obj.id, 0)

    def get_n_done_jobs(self, obj):
        if not obj: return 0
        return self._get_n_done_jobs().get(obj.id, 0)

    def get_n_todo_jobs(self, obj):
        if not obj: return 0
        return self._get_n_todo_jobs().get(obj.id, 0)

    class Meta:
        model = CodingJob


class CodingJobViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingJobSerializer
    model_key = "codingjob"
    model = CodingJob
    search_fields = (
        "id", "name", "unitschema__name", "articleschema__name",
        "insertuser__username", "coder__username"
    )

class CodingJobViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingJob
    model_serializer_class = CodingJobSerializer

    def filter_queryset(self, jobs):
        jobs = super(CodingJobViewSet, self).filter_queryset(jobs)
        return jobs.filter(project=self.project)

class CodingJobArticleViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, ArticleViewSetMixin,
                              DatatablesMixin, ReadOnlyModelViewSet):
    model = Article

    def filter_queryset(self, articles):
        articles = super(CodingJobArticleViewSet, self).filter_queryset(articles)
        return articles.filter(id__in=self.codingjob.articleset.articles.all())

class CodingJobArticleSentenceViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, ArticleViewSetMixin,
                                      SentenceViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = Sentence

    def filter_queryset(self, sentences):
        sentences = super(CodingJobArticleSentenceViewSet, self).filter_queryset(sentences)
        return sentences.filter(id__in=sbd.get_or_create_sentences(self.article))

class HighlighterViewSetMixin(AmCATViewSetMixin):
    model = Codebook
    model_key = "highlighter"

class CodingJobHighlighterViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, HighlighterViewSetMixin,
                                  DatatablesMixin, ReadOnlyModelViewSet):
    model = Codebook

    def filter_queryset(self, highlighters):
        highlighters = super(CodingJobHighlighterViewSet, self).filter_queryset(highlighters)
        return highlighters.filter(
            Q(pk__in=self.codingjob.articleschema.highlighters.all())|
            Q(pk__in=self.codingjob.unitschema.highlighters.all())
        )

class CodingJobCodingRuleViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, CodingRuleViewSetMixin,
                                 DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingRule
    model_serializer_class = CodingRuleSerializer

    def filter_queryset(self, rules):
        rules = super(CodingJobCodingRuleViewSet, self).filter_queryset(rules)
        return rules.filter(codingschema__pk__in=(self.codingjob.unitschema_id, self.codingjob.articleschema_id))

class CodingJobCodingSchemaFieldViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, CodingSchemaFieldViewSetMixin,
                                        DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingSchemaField
    model_serializer_class = CodingSchemaFieldSerializer

    def filter_queryset(self, fields):
        return super(CodingJobCodingSchemaFieldViewSet, self).filter_queryset(fields).filter(
            codingschema__pk__in=(self.codingjob.articleschema_id, self.codingjob.unitschema_id)
        )

