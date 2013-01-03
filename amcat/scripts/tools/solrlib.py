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
Library that makes it easier to access Solr features as used in Amcat3

Requires solrpy
"""
import solr, re
from amcat.models import article
from amcat.models import medium
from amcat.tools.toolkit import dateToInterval

from amcat.tools.table.table3 import DictTable
import time
import logging
log = logging.getLogger(__name__)


def doQuery(query, form, kargs, additionalFilters=None):
    filters = createFilters(form)
    if additionalFilters:
        filters += additionalFilters
    startTime = time.time()
    solrResponse = solr.SolrConnection('http://localhost:8983/solr').query(query,
                    fq=filters,
                    **kargs)
    log.info("found %s results in %2f ms! \r"
             % (len(solrResponse.results),((time.time() - startTime) * 1000)))
    return solrResponse


def parseSolrHighlightingToArticles(solrResponse):
    scoresDict = dict((x['id'], int(x['score'])) for x in solrResponse.results)
    articleids = map(int, solrResponse.highlighting.keys())
    articlesDict = article.Article.objects.defer('text').in_bulk(articleids)
    for articleid, highlights in solrResponse.highlighting.iteritems():
        articleid = int(articleid)
        if articleid not in articlesDict: continue
        a = articlesDict[articleid]
        a.highlightedHeadline = highlights.get('headline')
        a.highlightedText = highlights.get('body')
        a.hits = scoresDict[articleid]
        yield a


def getContext(snippet):
    """
    returns a dict which splits the snippet in the part before the first hit,
    the hit itself and after the hit.
    Hits after the first hit are surrounded by [[brackets]]
    """
    split = re.split('</?em>', snippet, 2)
    if not split or len(split) < 2:
        return None
    return {'before':split[0], 'hit':split[1],
            'after':split[2].replace('<em>', '[[').replace('</em>', ']]')}


def parseSolrHighlightingToContextDict(solrResponse):
    result = {}
    for articleid, highlights in solrResponse.highlighting.iteritems():
        item = {}
        highlightedHeadline = highlights.get('headline')
        if highlightedHeadline:
            item['headline'] = getContext(highlightedHeadline[0])
            item['text'] = item['headline']
        else:
            highlightedText = highlights.get('body')
            if highlightedText:
                item['text'] = getContext(highlightedText[0])
        result[int(articleid)] = item
    return result


def highlightArticles(form, snippets=3):
    #http://localhost:8983/solr/select/?indent=on&q=des&fl=id,headline,body&hl=true
    #   &hl.fl=body,headline&hl.snippets=3&hl.mergeContiguous=true
    #   &hl.usePhraseHighlighter=true&hl.highlightMultiTerm=true
    query = '(%s)' % ') OR ('.join([q.query for q in form['queries']])
    kargs = dict(
        highlight=True,
        fields="id,score,body,headline",
        hl_fl="body,headline",
        hl_usePhraseHighlighter='true',
        hl_highlightMultiTerm='true',
        hl_snippets=snippets,
        hl_mergeContiguous='true',
        start=form['start'],
        rows=form['length'])
    solrResponse = doQuery(query, form, kargs)
    return parseSolrHighlightingToArticles(solrResponse)



def getArticles(form):
    #if len(queries) == 1:
    query = '(%s)' % ') OR ('.join([q.query for q in form['queries']])
    kargs = dict(
            fields="id,score",
            rows=form['length']
            )

    if form['sortColumn']:
        if form['sortColumn'] == 'medium__id': form['sortColumn'] = 'mediumid'
        if form['sortColumn'] not in ('id', 'date', 'mediumid', 'score', 'headline'):
            raise Exception('Cannot sort on %s' % form['sortColumn'])
        kargs['sort'] = '%s %s' % (form['sortColumn'], form['sortOrder'])

    kargsMainQuery = kargs.copy()

    kargsMainQuery.update(dict(
        start=form['start']
        ))

    if 'keywordInContext' in form['columns']:
        kargsMainQuery.update(dict(
            highlight=True,
            fields="id,score,body",
            hl_fl="body",
            hl_usePhraseHighlighter='true',
            hl_highlightMultiTerm='true',
            hl_snippets=1,
            hl_mergeContiguous='false',
        ))

    solrResponse = doQuery(query, form, kargsMainQuery)

    if 'keywordInContext' in form['columns']:
        contextDict = parseSolrHighlightingToContextDict(solrResponse)
        #log.debug(contextDict)
    else:
        contextDict = {}

    articleids = [x['id'] for x in solrResponse.results]

    hitsTable = DictTable(0)
    hitsTable.rowNamesRequired = True

    if 'hits' in form['columns']:
        if len(form['queries']) > 1:
            additionalFilters = [' OR '.join(['id:%d' % id for id in articleids])]
            for singleQuery in form['queries']:
                hitsTable.columns.add(singleQuery.label)
                solrResponseSingleQuery = doQuery(singleQuery.query, form, kargs, additionalFilters)
                #articleIdList = []
                for d in solrResponseSingleQuery.results:
                    articleid = int(d['id'])
                    #articleIdList.append(articleid)
                    hits = int(d['score'])
                    log.info('add %s %s %s' % (articleid, singleQuery.label, hits))
                    hitsTable.addValue(articleid, singleQuery.label, hits)
        else: # only 1 query
            queryLabel = form['queries'][0].label
            hitsTable.columns.add(queryLabel)
            #articleIdList = []
            for d in solrResponse.results:
                articleid = int(d['id'])
                #articleIdList.append(articleid)
                hits = int(d['score'])
                #hitsTable.addValue(query, articleid, hits)
                hitsTable.addValue(articleid, queryLabel, hits)


    articlesDict = (article.Article.objects.defer('text')
                    .select_related('medium__name').in_bulk(articleids))
    result = []
    for articleid in articleids:
        if articleid not in articlesDict: continue
        a = articlesDict[articleid]
        a.hits = hitsTable.getNamedRow(articleid)
        a.keywordInContext = contextDict.get(articleid)
        result.append(a)
    return result

def getStats(statsObj, form):
    query = '(%s)' % ') OR ('.join([q.query for q in form['queries']])

    kargs = dict(
                fields="date",
                start=0,
                rows=1,
                sort='date asc')
    solrResponse = doQuery(query, form, kargs)
    statsObj.articleCount = solrResponse.numFound

    if solrResponse.numFound == 0:
        return

    statsObj.firstDate = solrResponse.results[0]['date']

    kargs = dict(
                fields="date",
                start=0,
                rows=1,
                sort='date desc')
    solrResponse = doQuery(query, form, kargs)

    statsObj.lastDate = solrResponse.results[0]['date']

def articleids(form):
    """get only the articleids for a query"""
    query = '(%s)' % ') OR ('.join([q.query for q in form['queries']])
    kargs = dict(fields="id", start=form['start'], rows=form['length'], score=False)
    solrResponse = doQuery(query, form, kargs)
    return [x['id'] for x in solrResponse.results]

def articleidsDict(form):
    """get only the articleids for a query"""
    result = {}
    for query in form['queries']:
        kargs = dict(fields="id", start=form['start'], rows=form['length'], score=False)
        solrResponse = doQuery(query.query, form, kargs)
        result[query.label] = [x['id'] for x in solrResponse.results]
    return result

mediumCache = {}
def mediumidToObj(mediumid):
    try:
        return mediumCache[mediumid]
    except KeyError:
        mediumCache[mediumid] = medium.Medium.objects.get(pk=mediumid)
        return mediumCache[mediumid]


def increaseCounter(table, x, y, a, counterLambda):
    table.addValue(x, y, table.getValue(x, y) + counterLambda(a))

def basicAggregate(form):
    """aggregate by using a counter"""
    table = DictTable(0)
    table.rowNamesRequired = True
    queries = form['queries']
    xAxis = form['xAxis']
    yAxis = form['yAxis']
    counterType = form['counterType']
    dateInterval = form['dateInterval']
    rowLimit = 1000000
    singleQuery = '(%s)' % ') OR ('.join([q.query for q in form['queries']])
    if counterType == 'numberOfHits':
        counterLambda = lambda a: int(a['score'])
    else:
        counterLambda = lambda a: 1

    if xAxis == 'medium' and yAxis == 'searchTerm':
        for query in queries:
            solrResponse = doQuery(query.query, form, dict(fields="score,mediumid", rows=rowLimit))
            table.columns.add(query.label)
            for a in solrResponse.results:
                x = mediumidToObj(a['mediumid'])
                y = query.label
                increaseCounter(table, x, y, a, counterLambda)
    elif xAxis == 'medium' and yAxis == 'total':
        solrResponse = doQuery(singleQuery, form, dict(fields="score,mediumid", rows=rowLimit))
        for a in solrResponse.results:
            x = mediumidToObj(a['mediumid'])
            y = '[total]'
            increaseCounter(table, x, y, a, counterLambda)
    elif xAxis == 'date' and yAxis == 'total':
        solrResponse = doQuery(singleQuery, form, dict(fields="score,date", rows=rowLimit))
        for a in solrResponse.results:
            x = dateToInterval(a['date'], dateInterval)
            y = '[total]'
            increaseCounter(table, x, y, a, counterLambda)
    elif xAxis == 'date' and yAxis == 'medium':
        solrResponse = doQuery(singleQuery, form, dict(fields="score,date,mediumid", rows=rowLimit))
        counterDict = {}
        for a in solrResponse.results:
            x = dateToInterval(a['date'], dateInterval)
            y = mediumidToObj(a['mediumid'])
            increaseCounter(table, x, y, a, counterLambda)
    elif xAxis == 'date' and yAxis == 'searchTerm':
        for query in queries:
            solrResponse = doQuery(query.query, form, dict(fields="score,date", rows=rowLimit))
            table.columns.add(query.label)
            for a in solrResponse.results:
                x = dateToInterval(a['date'], dateInterval)
                y = query.label
                increaseCounter(table, x, y, a, counterLambda)
    else:
        raise Exception('%s %s combination not possible' % (xAxis, yAxis))
    return table



def createFilters(form):
    """ takes a form as input and ceate filter queries for start/end date, mediumid and set """
    startDateTime = (form['startDate'].strftime('%Y-%m-%dT00:00:00.000Z')
                     if 'startDate' in form else '*')
    endDateTime = form['endDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'endDate' in form else '*'
    result = []
    if startDateTime != '*' or endDateTime != '*': # if at least one of the 2 is a date
        result.append('date:[%s TO %s]' % (startDateTime, endDateTime))
    if 'mediums' in form:
        mediumidQuery = ('mediumid:%d' % m.id for m in form['mediums'])
        result.append(' OR '.join(mediumidQuery))
    if 'articleids' in form:
        articleidQuery = ('id:%d' % a for a in form['articleids'])
        result.append(' OR '.join(articleidQuery))
    if 'articlesets' in form and form['articlesets']:
        setsQuery = ('sets:%d' % s.id for s in form['articlesets'])
        result.append(' OR '.join(setsQuery))
    else:
        log.warn("PROJECTS: %s/%r" % (type(form['projects']), form['projects']))
        projectQuery = ('projectid:%d' % p.id for p in form['projects'])
        result.append(' OR '.join(projectQuery))


    return result
