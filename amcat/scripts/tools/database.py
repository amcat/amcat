"""
A number of functions that help the Amcat3 selection page to retrieve selections from the database
"""

from amcat.models import ArticleSet
from amcat.models import article
from django.db.models import Q
from amcat.tools.djangotoolkit import db_supports_distinct_on

def getQuerySet(projects=None, articlesets=None, mediums=None, startDate=None, endDate=None, articleids=None, **kargs):
    queryset = article.Article.objects

    if not articlesets and projects:
        # Force Django to prefetch all articleset ids instead of letting the db do
        # it. See issue https://code.google.com/p/amcat/issues/detail?id=432.
        articlesets = ArticleSet.objects.filter(
            Q(project__id=projects)|Q(projects_set__id=projects)
        ).values_list("id", flat=True)

    if articlesets:
        queryset = queryset.filter(articlesets_set__in=articlesets)
    else:
        raise ValueError("Either projects or article sets needs to be specified")

    if mediums:
        queryset = queryset.filter(medium__in=mediums)
    if startDate:
        queryset = queryset.filter(date__gte=startDate)
    if endDate:
        queryset = queryset.filter(date__lt=endDate)
    if articleids:
        queryset = queryset.filter(id__in=articleids)

    if db_supports_distinct_on():
        return queryset.distinct("pk")

    return queryset.distinct()

