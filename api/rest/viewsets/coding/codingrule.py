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
    model = CodingRule
    parsed_condition = serializers.SerializerMethodField('get_parsed_condition')

    def get_parsed_condition(self, obj):
        try:
            return codingruletoolkit.to_json(codingruletoolkit.parse(obj), serialise=False)
        except (ValidationError, SyntaxError):
            return None

    class Meta:
        model = CodingRule

class CodingRuleViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingRuleSerializer
    model_key = "coding_rule"
    model = CodingRule


class CodingRuleActionSerializer(AmCATModelSerializer):
    model = CodingRuleAction

class CodingRuleActionViewSetMixin(AmCATViewSetMixin):
    model_serializer_class = CodingRuleActionSerializer
    model_key = "coding_rule_action"
    model = CodingRuleAction

class CodingRuleActionViewSet(CodingRuleActionViewSetMixin, DatatablesMixin, ReadOnlyModelViewSet):
    model = CodingRuleAction
    model_serializer_class = CodingRuleActionSerializer
