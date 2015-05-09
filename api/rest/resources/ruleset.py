from amcat.models import RuleSet
from api.rest.resources.amcatresource import AmCATResource

class RuleSetResource(AmCATResource):
    model = RuleSet
    queryset = RuleSet.objects.all()
