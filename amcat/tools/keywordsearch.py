
from django.db import models
import collections
import logging
from amcat.tools.amcates import ES

log = logging.getLogger(__name__)

def _get_filter_date(cleaned_data, prop):
    if prop not in cleaned_data: return "*"
    return cleaned_data[prop].isoformat() + "Z"

FILTER_FIELDS = {"mediums" : "mediumid", "article_ids" : "ids", "articlesets" : "sets",
                 "start_date" : "start_date", "end_date": "end_date"}

def _serialize(x):
    if isinstance(x, collections.Iterable):
        return [_serialize(e) for e in x]
    elif isinstance(x, models.Model):
        return x.id
    return x

def filters_from_form(form_data):
    return {FILTER_FIELDS[k] : _serialize(v)
            for (k,v) in form_data.iteritems() if v and k in FILTER_FIELDS}

def getArticles(form):
    fields=["id", "score"]

    sort = form.get('sortColumn', None)

    if 'keywordInContext' in form['columns']:
        raise NotImplementedError()
    if 'hits' in form['columns']:
        raise NotImplementedError()

    query = form['query']
    filters = filters_from_form(form)
    
    log.info("Query: {query!r}, with filters: {filters}".format(**locals()))

    
    
    solrResponse = doQuery(form['query'], form, fields)


    articlesDict = (article.Article.objects.defer('text')
                    .select_related('medium__name').in_bulk(article_ids))
    result = []
    for articleid in article_ids:
        if articleid not in articlesDict: continue
        a = articlesDict[articleid]
        a.hits = hitsTable.getNamedRow(articleid)
        a.keywordInContext = contextDict.get(articleid)
        result.append(a)
    return result
