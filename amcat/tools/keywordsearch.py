
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
    fields = ['mediumid', 'date', 'headline']
    
    sort = form.get('sortColumn', None)

    if 'keywordInContext' in form['columns']:
        raise NotImplementedError()
    if 'hits' in form['columns']:
        raise NotImplementedError()


    query = form['query']
    kargs = {}
    if form['highlight']:
        kargs["highlight" if query else "lead"] = True
        
    filters = filters_from_form(form)
    
    log.info("Query: {query!r}, with filters: {filters}".format(**locals()))

    return ES().query(query, filters=filters, fields=fields, sort=sort, **kargs)

