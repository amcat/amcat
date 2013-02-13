"""
A number of functions that help the Amcat3 selection page to retrieve selections from the database
"""

from amcat.models import article
from django.db.models import Q

def getQuerySet(projects=None, articlesets=None, mediums=None, startDate=None, endDate=None, articleids=None, **kargs):
    queryset = article.Article.objects

    if articlesets:
        queryset = queryset.filter(articlesets_set__in=articlesets)
    elif projects:
        queryset = queryset.filter(
            Q(articlesets_set__project__in=projects)|
            Q(articlesets_set__projects_set__in=projects)
        )
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

    return queryset.distinct()
