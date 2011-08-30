"""
Library that makes it easier to access Solr features as used in Amcat3

Requires solrpy
"""
import solr
from amcat.model import article

# class HighlightedArticle(article.Article): not working..
    # highlightedHeadline = None
    # highlightedBody = None
    # hits = None

def createSolrConnection():
    # create a connection to a solr server
    return solr.SolrConnection('http://localhost:8983/solr')

def highlight(query, snippets=3, start=0, rows=20, filters=[]):
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
                    rows=rows, 
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
        
def articleids(query, start=0, rows=9999, filters=[]):
    response = createSolrConnection().query(query, fields="id", start=start, rows=rows, fq=filters, score=False)
    #articlesDict = article.Article.objects.defer('text').in_bulk(x['id'] for x in response.results) 
    return (article.Article(x['id']) for x in response.results)
    
    
def aggregate(query, xaxis, yaxis, filters=[]):
    #http://localhost:8983/solr/select?indent=on&q=projectid:291&fl=name&facet=true&facet.field=projectid&facet.field=mediumid&facet.query=projectid:291%20AND%20mediumid:7
    response = createSolrConnection().query(query, fields="id", facet='true', facet_field='projectid', fq=filters, score=False)
    
    
def createFilters(form):
    """ takes a form as input and ceate filter queries for start/end date, mediumid and set """
    startDateTime = form['startDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'startDate' in form else '*'
    endDateTime = form['endDate'].strftime('%Y-%m-%dT00:00:00.000Z') if 'endDate' in form else '*'
    result = []
    if startDateTime != '*' and endDateTime != '*': # if at least one of the 2 is a date
        result.append('date:[%s TO %s]' % (startDateTime, endDateTime))
    if 'mediums' in form:
        mediumidQuery = ('mediumid:%d' % m.id for m in form['mediums'])
        result.append(' OR '.join(mediumidQuery))
    return result
    