
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import RuleSet, Rule
from api.rest.viewset import AmCATViewSetMixin
from api.rest.serializer import AmCATModelSerializer

from api.rest.viewsets.articleset import ArticleSetViewSetMixin
from api.rest.viewsets.article import ArticleViewSetMixin
from api.rest.viewsets.project import ProjectViewSetMixin
from api.rest.mixins import DatatablesMixin
from amcat.tools.amcatxtas import ANALYSES, get_result

class RulesetViewSetMixin(AmCATViewSetMixin):
    model_key = "ruleset"
    model = RuleSet

class RulesetViewSet(RulesetViewSetMixin, ReadOnlyModelViewSet):
    model_serializer_class =  AmCATModelSerializer
    model = RuleSet

    def filter_queryset(self, queryset):
        return queryset

class RuleViewSetMixin(AmCATViewSetMixin):
    model_key = "rule"
    model = Rule

class RuleViewSet(RulesetViewSetMixin, RuleViewSetMixin, ReadOnlyModelViewSet):
    model_serializer_class =  AmCATModelSerializer
    model = Rule

    def filter_queryset(self, queryset):
        return queryset.filter(ruleset_id=self.kwargs['ruleset'])


from rest_framework.serializers import Serializer
from api.rest.serializer import AmCATModelSerializer

class RulesetSerializer(AmCATModelSerializer):

    def to_native(self, ruleset):
        from syntaxrules import SyntaxTree
        if self.many is False: # explicit compare because we don't want None
            # Get parse
            module = ruleset.preprocessing
            saf = get_result(self.context['article'], module)
            t = SyntaxTree(saf)

            if self.context['preprocess']:
                r = RuleSet.objects.get(pk=int(self.context['preprocess']))
                t.apply_ruleset(r.get_ruleset())

            # Apply rules
            t.apply_ruleset(ruleset.get_ruleset())
            return list(t.get_roles())

        res = super(RulesetSerializer,self).to_native(ruleset)
        return res

class ArticleRulesetViewSet(ProjectViewSetMixin, ArticleSetViewSetMixin, ArticleViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model_key = "ruleset"
    model = RuleSet
    model_serializer_class = RulesetSerializer

    def get_serializer_context(self):
        ctx = super(ArticleRulesetViewSet, self).get_serializer_context()
        ctx['article'] = int(self.kwargs['article'])
        ctx['preprocess'] = int(self.request.GET.get('preprocess'))
        return ctx
