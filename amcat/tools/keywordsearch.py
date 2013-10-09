
from django.db import models
import collections
import logging
from amcat.tools.amcates import ES
from amcat.tools.table import table3

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

def getTable(form):
    table = table3.DictTable(default=0)
    table.rowNamesRequired = True
    query = form['query']
    xAxis = form['xAxis']
    yAxis = form['yAxis']
    dateInterval = form['dateInterval']
    filters = filters_from_form(form)

    # ignore yaxis for a second
    group_by = form['xAxis']
    if group_by == 'medium': group_by = 'mediumid'
    for group, n in ES().aggregate_query(query, filters, group_by, dateInterval):
        table.addValue(str(group), 'total', n)
    return table

                                 
def get_statistics(form):
    query = form['query']
    filters = filters_from_form(form)
    return ES().statistics(query, filters)
    
