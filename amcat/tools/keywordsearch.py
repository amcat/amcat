#TODO: NOTE: This module replaces the old 'solrlib', but I feel it can be removed
# entirely. The 'getTable' / 'getArticles' can move either to their respective
# webscripts, or to the REST API. The form handling should just go to the form.

from django.db import models
import collections
import logging
from amcat.tools.amcates import ES
from amcat.tools.table import table3
from amcat.models import Medium

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
    fields = ['mediumid', 'date', 'headline', 'medium']
    
    sort = form.get('sortColumn', None)

    if 'keywordInContext' in form['columns']:
        raise NotImplementedError()
        

    query = form['query']
    kargs = {}
    if form['highlight']:
        kargs["highlight" if query else "lead"] = True
        
    filters = filters_from_form(form)
    
    log.info("Query: {query!r}, with filters: {filters}".format(**locals()))

    result = list(ES().query(query, filters=filters, fields=fields, sort=sort, **kargs))

    if 'hits' in form['columns']:
        # add hits columns
        def add_hits_column(r):
            r.hits = {q.label : 0 for q in form['queries']}
            return r
            
        result_dict = {r.id : add_hits_column(r) for r in result}
        f = dict(ids=list(result_dict.keys()))

        for q in form['queries']:
            for hit in ES().query(q.query, filters=f, fields=[]):
                result_dict[hit.id].hits[q.label] = hit.score
    return result
    
def getTable(form):
    table = table3.DictTable(default=0)
    table.rowNamesRequired = True
    dateInterval = form['dateInterval']
    group_by = form['xAxis']
    filters = filters_from_form(form)

    yAxis = form['yAxis']
    if yAxis == 'total':
        query = form['query']
        _add_column(table, 'total', query, filters, group_by, dateInterval)
    elif yAxis == 'medium':
        query = form['query']
        media = Medium.objects.filter(pk__in=ES().list_media(query, filters)).only("name")
        
        for medium in sorted(media):
            filters['mediumid'] = medium.id
            name = u"{medium.id} - {}".format(medium.name.replace(",", " ").replace(".", " "), **locals())
            _add_column(table, name, query, filters, group_by, dateInterval)
    elif yAxis == 'searchTerm':
        for q in form['queries']:
            _add_column(table, q.label, q.query, filters, group_by, dateInterval)
    else:
        raise Exception('yAxis {yAxis} not recognized'.format(**locals()))

    return table

def _add_column(table, column_name, query, filters, group_by, dateInterval):
    for group, n in ES().aggregate_query(query, filters, group_by, dateInterval):
        table.addValue(unicode(group), column_name, n)
    

                                 
def get_statistics(form):
    query = form['query']
    filters = filters_from_form(form)
    return ES().statistics(query, filters)
    
