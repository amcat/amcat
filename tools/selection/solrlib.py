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
import solr
from amcat.model import article
from amcat.model import medium

from amcat.tools.table.table3 import DictTable

# class HighlightedArticle(article.Article): not working..
    # highlightedHeadline = None
    # highlightedBody = None
    # hits = None

def createSolrConnection():
    # create a connection to a solr server
    return solr.SolrConnection('http://localhost:8983/solr')

def highlight(query, snippets=3, start=0, length=20, filters=[]):
    #http://localhost:8983/solr/select/?indent=on&q=des&fl=id,headline,body&hl=true&hl.fl=body,headline&hl.snippets=3&hl.mergeContiguous=true&hl.usePhraseHighlighter=true&hl.highlightMultiTerm=true
    response = createSolrConnection().query(query, 
                    highlight=True, 
                    fields="id,score,body,headline", 
                    hl_fl="body,headline", 
                    hl_usePhraseHighlighter='true', 
                    hl_highlightMultiTerm='true',
                    hl_snippets=snippets,
                    hl_mergeContiguous='true', 
                    start=start, 
                    rows=length, 
                    fq=filters)
    scoresDict = dict((x['id'], int(x['score'])) for x in response.results)
    articleids = map(int, response.highlighting.keys())
    articlesDict = article.Article.objects.defer('text').in_bulk(articleids)
    result = []
    for articleid, highlights in response.highlighting.iteritems():
        a = articlesDict[int(articleid)]
        a.highlightedHeadline = highlights.get('headline')
        a.highlightedText = highlights.get('body')
        a.hits = scoresDict[int(articleid)]
        result.append(a)
    return result
    
    
def getArticles(query, start=0, length=20, filters=[]):
    response = createSolrConnection().query(query, 
                    fields="id,score,body,headline", 
                    start=start, 
                    rows=length, 
                    fq=filters)
    
    articleids = [x['id'] for x in response.results]
    articlesDict = article.Article.objects.defer('text').in_bulk(articleids)
    result = []
    for d in response.results:
        articleid = d['id']
        a = articlesDict[int(articleid)]
        a.hits = d['score']
        result.append(a)
    return result
        
def articleids(query, start=0, rows=9999, filters=[]):
    """get only the articleids for a query"""
    response = createSolrConnection().query(query, fields="id", start=start, rows=rows, fq=filters, score=False)
    #articlesDict = article.Article.objects.defer('text').in_bulk(x['id'] for x in response.results) 
    return (article.Article(x['id']) for x in response.results) # todo, change this for db efficiency
    
    
def aggregate(queries, xAxis, yAxis, filters=[]):
    """aggregate using the Solr aggregation function (facet search)
    
    not fully working!!
    """
    #http://localhost:8983/solr/select?indent=on&q=projectid:291&fl=name&facet=true&facet.field=projectid&facet.field=mediumid&facet.query=projectid:291%20AND%20mediumid:7
    
    #http://localhost:8983/solr/select?indent=on&q=test&fq=projectid:291&fl=name&facet=true&&facet.field=mediumid
    #facet total by medium: http://localhost:8983/solr/select?indent=on&q=test&fq=projectid:291&fl=id&rows=0&facet=true&facet.field=mediumid
    table = DictTable(0)
    if xAxis == 'medium' and yAxis == 'searchTerm':
        for query in queries:
            print query
            response = createSolrConnection().query(query, fields="id", facet='true', facet_field='mediumid', facet_mincount=1, fq=filters, score=False, rows=0)
            for mediumid, count in response.facet_counts['facet_fields']['mediumid'].items():
                print mediumid, count
                m = medium.Medium.objects.get(pk=mediumid)
                table.addValue(m, query, count)
    elif xAxis == 'date' and yAxis == 'medium':
        pass
    elif xAxis == 'date' and yAxis == 'searchTerm':
        pass
    else:
        raise Exception('%s %s combination not possible' % (xAxis, yAxis))
    return table
    
    
    
def dateToInterval(date, interval):
    if interval == 'day':
        return date.strftime('%Y-%m-%d')
    elif interval == 'week':
        return date.strftime('%Y-%W')
    elif interval == 'month':
        return date.strftime('%Y-%m')
    elif interval == 'quarter':
        return '%s-%s' % (date.year, (date.month-1)//3 + 1)
    elif interval == 'year':
        return date.strftime('%Y')
    raise Exception('invalid interval')
        
    
def basicAggregate(queries, xAxis, yAxis, counter, dateInterval=None, filters=[]):
    """aggregate by using a counter"""
    table = DictTable(0)
    if xAxis == 'medium' and yAxis == 'searchTerm':
        for query in queries:
            response = createSolrConnection().query(query, fields="score,mediumid", fq=filters, rows=1000)
            for a in response.results:
                x = str(a['mediumid'])
                y = query
                table.addValue(x, y, table.getValue(x, y) + (a['score'] if counter == 'numberOfHits' else 1))
    elif xAxis == 'date' and yAxis == 'medium':
        for query in queries:
            response = createSolrConnection().query(query, fields="score,date,mediumid", fq=filters, rows=1000)
            for a in response.results:
                x = dateToInterval(a['date'], dateInterval)
                y = str(a['mediumid'])
                table.addValue(x, y, table.getValue(x, y) + (a['score'] if counter == 'numberOfHits' else 1))
    elif xAxis == 'date' and yAxis == 'searchTerm':
        for query in queries:
            response = createSolrConnection().query(query, fields="score,date", fq=filters, rows=1000)
            for a in response.results:
                x = dateToInterval(a['date'], dateInterval)
                y = query
                table.addValue(x, y, table.getValue(x, y) + (a['score'] if counter == 'numberOfHits' else 1))
    else:
        raise Exception('%s %s combination not possible' % (xAxis, yAxis))
    return table
            
    
    
def createFilters(form):
    """ takes a form as input and ceate filter queries for start/end date, mediumid and set """
    startDateTime = form['startDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'startDate' in form else '*'
    endDateTime = form['endDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'endDate' in form else '*'
    result = []
    if startDateTime != '*' or endDateTime != '*': # if at least one of the 2 is a date
        result.append('date:[%s TO %s]' % (startDateTime, endDateTime))
    if 'mediums' in form:
        mediumidQuery = ('mediumid:%d' % m.id for m in form['mediums'])
        result.append(' OR '.join(mediumidQuery))
    if 'sets' in form:
        setsQuery = ('sets:%d' % s.id for s in form['sets'])
        result.append(' OR '.join(setsQuery))
    
    projectQuery = ('projectid:%d' % p.id for p in form['projects'])
    result.append(' OR '.join(projectQuery))
    return result
    