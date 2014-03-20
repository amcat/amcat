
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import RuleSet, Rule
from api.rest.viewset import AmCATViewSetMixin
from api.rest.serializer import AmCATModelSerializer

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
    
