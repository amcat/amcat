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
import json

from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.viewsets import ReadOnlyModelViewSet
from amcat.models import CodingRule, CodingRuleAction
from amcat.models.coding import codingruletoolkit
from api.rest.mixins import DatatablesMixin
from api.rest.serializer import AmCATModelSerializer
from api.rest.viewset import AmCATViewSetMixin

__all__ = (
    "CodingRuleSerializer", "CodingRule", "CodingRuleViewSetMixin",
    "CodingRuleActionViewSetMixin", "CodingRuleActionViewSet",
    "CodingRuleActionSerializer"

)


class CodingRuleSerializer(AmCATModelSerializer):
    parsed_condition = serializers.SerializerMethodField()

    def get_parsed_condition(self, obj):
        try:
            return codingruletoolkit.to_json(codingruletoolkit.parse(obj), serialise=False)
        except (ValidationError, SyntaxError) as e:
            return json.dumps(str(e))


    class Meta:
        model = CodingRule

class CodingRuleViewSetMixin(AmCATViewSetMixin):
    serializer_class = CodingRuleSerializer
    model_key = "coding_rule"
    queryset = CodingRule.objects.all()
    model = CodingRule


class CodingRuleActionSerializer(AmCATModelSerializer):
    class Meta:
        model = CodingRuleAction

class CodingRuleActionViewSetMixin(AmCATViewSetMixin):
    serializer_class = CodingRuleActionSerializer
    model_key = "coding_rule_action"
    model = CodingRuleAction
    queryset = CodingRuleAction.objects.all()

class CodingRuleActionViewSet(CodingRuleActionViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    serializer_class = CodingRuleActionSerializer
    queryset = CodingRuleAction.objects.all()
    model = CodingRuleAction
