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
    response = createSolrConnection().query(query, highlight=True, fields="id,score,body,headline", hl_fl="body,headline", hl_usePhraseHighlighter='true', hl_highlightMultiTerm='true',hl_snippets=snippets,hl_mergeContiguous='true', start=start, rows=rows, fq=filters)
    #print response.highlighting.__dict__
    scoresDict = dict((x['id'], x['score']) for x in response.results)
    # for hit in response.results:
        # print hit
    #print scores
    articleids = map(int, response.highlighting.keys())
    #print articleids
    articlesDict = article.Article.objects.defer('text').in_bulk(articleids)
    #print articles
    result = []
    for articleid, highlights in response.highlighting.iteritems():
        a = articlesDict[int(articleid)]
        a.highlightedHeadline = highlights.get('headline')
        a.highlightedText = highlights.get('body')
        a.hits = scoresDict[int(articleid)]
        result.append(a)
    return result
        
