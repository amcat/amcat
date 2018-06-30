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

"""
AmCAT-specific adaptations to rest_framework filters
(using django_filters)
activated by settings.REST_FRAMEWORK['FILTER_BACKEND']
"""
import logging

from django_filters import filterset, FilterSet, ModelMultipleChoiceFilter
from django_filters.filters import NumberFilter
from django.db import models
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

log = logging.getLogger(__name__)

# Monkey patch filterset for autofield - no idea why it's not in that list
filterset.FILTER_FOR_DBFIELD_DEFAULTS[models.AutoField] = dict(filter_class=NumberFilter)

# Should listen to ORDERING_PARAM (says documentation) but it doesn't :-(
OrderingFilter.ordering_param = settings.REST_FRAMEWORK['ORDERING_PARAM']


class InFilter(ModelMultipleChoiceFilter):
    """Filter for {'pk':[1,2,3]} / pk=1&pk=2 queries"""

    def filter(self, qs, value):
        # Perform 'IN' query on given primary keys
        value = list(value)
        if not all(type(v) is int for v in value):
            value = [v.pk for v in value]
        return super().filter(qs, value)


class PrimaryKeyFilterSet(FilterSet):
    pk = InFilter(name='id', queryset=None)

    def __init__(self, *args, **kwargs):
        super(PrimaryKeyFilterSet, self).__init__(*args, **kwargs)
        self.filters["pk"].field.queryset = self.queryset


class DjangoPrimaryKeyFilterBackend(DjangoFilterBackend):
    """
    Overrides default_filter_set on on DjangoFilterBackend to add a `pk` property
    refering to InFilter, which allows filtering on primary keys with an OR filter.
    """
    default_filter_set = PrimaryKeyFilterSet


def _strip_direction(field):
    return field[1:] if field.startswith("-") else field


def _get_ordering(mapping, fields):
    for field in fields:
        # We need to check for signs in front of the field which indicate direction
        mapped_field = mapping.get(_strip_direction(field), field)

        if field.startswith("-") and not mapped_field.startswith("-"):
            yield "-" + mapped_field
        else:
            yield mapped_field


class MappingOrderingFilter(OrderingFilter):
    """
    Just like OrderingFilter, this filter provides a way of ordering query results.
    However, it also accounts for an extra property `ordering_mapping` which can
    translate 'view' columns to 'real' database columns.

    Consider the following pseudo-code:

    >>> class ArticleSerializer:
    >>>     aset_name = Field(lambda a: a.articleset.name)
    >>>
    >>> class ArticleViewSet:
    >>>     serializer_class = ArticleSerializer

    We would like to allow ordering on 'aset_name', even though the user of
    the API shouldn't need to know about the origin of the property (thus abstracting
    database models). In order to do this, we define a property:

    >>> class ArticleViewSet:
    >>>     serializer_class = ArticleSerializer
    >>>     ordering_fields = ("aset_name", "articleset__name")
    >>>     ordering_mapping = {"aset_name": "articleset__name"}
    """
    def get_ordering(self, request, queryset, view):
        ordering = super(MappingOrderingFilter, self).get_ordering(request, queryset, view)

        # Determine mapped values if ordering is a list
        if ordering is not None:
            mapping = getattr(self.view, "ordering_mapping", {})
            return list(_get_ordering(mapping, ordering))

        return ordering

    def filter_queryset(self, request, queryset, view):
        # Allow get_ordering to access current view
        self.view = view
        return super(MappingOrderingFilter, self).filter_queryset(request, queryset, view)

