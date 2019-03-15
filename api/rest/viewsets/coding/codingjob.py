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

from amcat.models import ArticleSet, Coding
from amcat.models.coding.codingjob import CodingJob
from amcat.models.article import Article
from amcat.models.sentence import  Sentence
from amcat.models.coding.codebook import Codebook
from amcat.models.coding.codingrule import CodingRule
from amcat.models.coding.codingschemafield import CodingSchemaField
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from amcat.models.coding.codedarticle import STATUS_COMPLETE, STATUS_IRRELEVANT, CodedArticle, STATUS_INPROGRESS, STATUS_NOTSTARTED
from amcat.tools import sbd
from amcat.tools.caching import cached
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin
from api.rest.viewsets.coding.codingschemafield import CodingSchemaFieldViewSetMixin, CodingSchemaFieldSerializer
from api.rest.viewsets.coding.codingrule import CodingRuleViewSetMixin, CodingRuleSerializer
from api.rest.viewsets.sentence import SentenceViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin, ArticleSerializer
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
    articleset = serializers.PrimaryKeyRelatedField(read_only=True)
    codings = serializers.SerializerMethodField('get_n_codings')
    articles = serializers.SerializerMethodField('get_n_articles')
    complete = serializers.SerializerMethodField('get_n_done_jobs')
    todo = serializers.SerializerMethodField('get_n_todo_jobs')

    def __init__(self, *args, **kwargs):
        """Initializes the Serializer
        @param use_caching: indicates whether the serializer should cache codingjobs' statistics
                            Defaults to True.
        """
        super(CodingJobSerializer, self).__init__(*args, **kwargs)
        
        self.use_caching = kwargs.pop('use_caching', True) 

    def to_internal_value(self, data):
        if 'insertuser' not in data:
            data['insertuser'] = self.context['request'].user.id
        return super().to_internal_value(data)

    @cached
    def _get_codingjob_ids(self):
        view = self.context["view"]
        if hasattr(view, "kwargs") and 'pk' in view.kwargs:
            return [int(view.kwargs['pk'])]

        else:
            try:
                f = view.paginate_queryset
            except AttributeError:
                f = lambda x: x  # noop
            pks = [cj.pk for cj in f(view.filter_queryset(view.get_queryset().order_by('id')))]
            return pks

    def _get_codingjobs(self):
        ids = self._get_codingjob_ids()
        return CodingJob.objects.filter(id__in=ids)

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
    def _get_n_codings(self):
        return dict(Coding.objects.filter(coded_article__codingjob_id__in=self._get_codingjob_ids())
                    .values('coded_article__codingjob_id').annotate(n=Count("id"))
                    .values_list('coded_article__codingjob_id', 'n'))

    @cached
    def _get_n_articles(self):
        return dict(self._get_codingjobs().annotate(n=Count("articleset__articles")).values_list("id", "n"))

    def get_n_articles(self, obj):
        if not obj: return 0

        if not self.use_caching:
            return obj.articleset.articles.count()

        return self._get_n_articles().get(obj.id, 0)

    def get_n_done_jobs(self, obj):
        if not obj: return 0
        
        if not self.use_caching:
            return CodedArticle.objects.filter(codingjob=obj, status__id__in=STATUS_DONE).count()
        
        return self._get_n_done_jobs().get(obj.id, 0)

    def get_n_todo_jobs(self, obj):
        if not obj: return 0
        
        if not self.use_caching:
            return CodedArticle.objects.filter(codingjob=obj, status__id__in=STATUS_TODO).count() 
        
        return self._get_n_todo_jobs().get(obj.id, 0)

    def get_n_codings(self, obj):
        if not obj: return 0
        return self._get_n_codings().get(obj.id, 0)

    def get_articleset(self, obj):
        return obj.articleset_id

    class Meta:
        model = CodingJob
        fields = '__all__'

class CodingJobViewSetMixin(AmCATViewSetMixin):
    queryset = CodingJob.objects.all()
    serializer_class = CodingJobSerializer
    model_key = "codingjob"
    model = CodingJob
    search_fields = (
        "id", "name", "unitschema__name", "articleschema__name",
        "insertuser__username", "coder__username"
    )

class CodingJobViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, DatatablesMixin, ModelViewSet):
    queryset = CodingJob.objects.all()
    serializer_class = CodingJobSerializer
    

    def retrieve(self, *args, **kwargs):
        return super(CodingJobViewSet, self).retrieve(use_caching=False, *args, **kwargs)
        
    def filter_queryset(self, jobs):
        jobs = super(CodingJobViewSet, self).filter_queryset(jobs)
        return jobs.filter(Q(project=self.project) | Q(linked_projects=self.project))
    

class CodingJobArticleViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, ArticleViewSetMixin,
                              DatatablesMixin, ReadOnlyModelViewSet):
    queryset = Article.objects.all()
    model = Article
    serializer_class = ArticleSerializer

    def filter_queryset(self, articles):
        articles = super(CodingJobArticleViewSet, self).filter_queryset(articles)
        return articles.filter(id__in=self.codingjob.articleset.articles.all())


class CodingJobArticleSentenceViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, ArticleViewSetMixin,
                                      SentenceViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    queryset = Sentence.objects.all()
    model = Sentence

    def filter_queryset(self, sentences):
        sentences = super(CodingJobArticleSentenceViewSet, self).filter_queryset(sentences)
        return sentences.filter(id__in=sbd.get_or_create_sentences(self.article))

class HighlighterViewSetMixin(AmCATViewSetMixin):
    model = Codebook
    model_key = "highlighter"

class CodingJobHighlighterViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, HighlighterViewSetMixin,
                                  DatatablesMixin, ReadOnlyModelViewSet):
    queryset = Codebook.objects.all()

    def filter_queryset(self, highlighters):
        highlighters = super(CodingJobHighlighterViewSet, self).filter_queryset(highlighters)
        return highlighters.filter(
            Q(pk__in=self.codingjob.articleschema.highlighters.all())|
            Q(pk__in=self.codingjob.unitschema.highlighters.all())
        )

class CodingJobCodingRuleViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, CodingRuleViewSetMixin,
                                 DatatablesMixin, ReadOnlyModelViewSet):
    queryset = CodingRule.objects.all()
    serializer_class = CodingRuleSerializer
    model = CodingRule

    def filter_queryset(self, rules):
        rules = super(CodingJobCodingRuleViewSet, self).filter_queryset(rules)
        return rules.filter(codingschema__pk__in=(self.codingjob.unitschema_id, self.codingjob.articleschema_id))

class CodingJobCodingSchemaFieldViewSet(ProjectViewSetMixin, CodingJobViewSetMixin, CodingSchemaFieldViewSetMixin,
                                        DatatablesMixin, ReadOnlyModelViewSet):
    queryset = CodingSchemaField.objects.all()
    serializer_class = CodingSchemaFieldSerializer
    model = CodingSchemaField

    def filter_queryset(self, fields):
        return super(CodingJobCodingSchemaFieldViewSet, self).filter_queryset(fields).filter(
            codingschema__pk__in=(self.codingjob.articleschema_id, self.codingjob.unitschema_id)
        )

