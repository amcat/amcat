"""
A number of functions that help the Amcat3 selection page to retrieve selections from the database
"""

from amcat.models import article

def getQuerySet(projects, articlesets=None, mediums=None, startDate=None, endDate=None, articleids=None, **kargs):
    queryset = article.Article.objects.filter(project__in=projects)
    if articlesets:
        queryset = queryset.filter(articleset__in=articlesets)
    if mediums:
        queryset = queryset.filter(medium__in=mediums)
    if startDate:
        queryset = queryset.filter(date__gte=startDate)
    if endDate:
        queryset = queryset.filter(date__lte=endDate)
    if articleids:
        queryset = queryset.filter(id__in=articleids)
    return queryset