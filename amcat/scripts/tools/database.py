"""
A number of functions that help the Amcat3 selection page to retrieve selections from the database
"""

from amcat.models import article

def getQuerySet(projects=None, articlesets=None, mediums=None, startDate=None, endDate=None, articleids=None, **kargs):
    queryset = article.Article.objects
    if articlesets:
        queryset = queryset.filter(articlesets__in=articlesets)
    elif projects: 
        queryset = queryset.filter(articlesets__project__in=projects)
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

    return queryset
