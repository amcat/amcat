from django.http import HttpResponse, HttpResponseBadRequest
from amcat.models.coding.codingjob import CodingJob
from amcat.models.article import Article
from django.core.cache import cache
import json
import snowballstemmer
import random

def articleschema(request):
    return highlight(request, 'articleschema')

def unitschema(request):
    return highlight(request, 'unitschema')

def highlight(request, schematype):
    codingjob_id = request.GET.get('codingjob_id')
    article_id = request.GET.get('article_id')

    # check paramaters
    if codingjob_id is None or article_id is None:
        return HttpResponseBadRequest()

    cj = CodingJob.objects.get(pk=codingjob_id)
    article = Article.objects.get(pk=article_id)

    keywords = []

    # create variable keywords list
    if schematype == "articleschema":
        schema = cj.articleschema
    else:
        schema = cj.unitschema
    for csf in schema.fields.all():
        keywords.append(csf.keywords)

    article_matrix = []
    current_parnr = 0;

    # create matrix article sentences
    for sentence in article.sentences.all():
        if sentence.parnr != current_parnr:
            article_matrix.append([])
            current_parnr = sentence.parnr
        article_matrix[-1].append(sentence.sentence)

    # get and respond with highlighting scores
    hash_value = highlighting_hash(article_matrix, keywords)
    result = from_cache(article_id, schema.id, hash_value)
    if result is None:
        ha = HighlighterArticles()
        result = ha.getHighlightingsArticle(article_matrix, keywords, None)
        to_cache(article_id, schema.id, hash_value, result)
    return HttpResponse(json.dumps(result), content_type='application/json')


def highlighting_hash(article_matrix, keywords):
    return hash(str(article_matrix) + ":" + str(keywords))


def from_cache(article_id, schema_id, hash_value):
    article_cache = cache.get("highlighting-{0}".format(article_id))
    if article_cache is None:
        return None
    codingjob_cache = None
    if schema_id in article_cache:
        codingjob_cache = article_cache[schema_id]
    if codingjob_cache is None:
        return None
    if not codingjob_cache['hash'] == hash_value:
        return None
    return codingjob_cache['value']

def to_cache(article_id, schema_id, hash_value, result):
    article_cache = cache.get("highlighting-{0}".format(article_id))
    if article_cache is None:
        article_cache = {}
    article_cache[schema_id] = {}
    article_cache[schema_id]['hash'] = hash_value
    article_cache[schema_id]['value'] = result
    cache.set("highlighting-{0}".format(article_id), article_cache)
    cache.close()


class HighlighterArticles:
#input: 
#article: two-dimensional array of the article: the first dimension corresponds to the paragraph, second corresponds to sentences. 
#variable_keywords: one-dimenstional array of comma-separated keywords
#variable_pages: array of the page numbers assigned to the variables (index identical to variable_keywords).
#output: three-dimensional array: paragraph-sentence-variable, meaning that for every sentence in a paragraph we have scores \in [0,1] giving the highlighting for each variable
    def getHighlightingsArticle(self, article, variable_keywords, variable_pages):
        stemmer = snowballstemmer.stemmer("german")
        for i in range(0, len(article)):
            for j in range(0, len(article[i])):
                article[i][j] = article[i][j].split(" ");
                for k in range(0, len(article[i][j])):
                    #article[i][j][k]=chrtran(article[i][j][k], goodchars, "")
                    article[i][j][k]=stemmer.stemWord(article[i][j][k])
     
 
        for i in range(0, len(variable_keywords)):
            #variable_keywords[i]=chrtran(variable_keywords[i], goodchars, "")
            variable_keywords[i]=stemmer.stemWord(variable_keywords[i])
     
        highlight = []
 
        for i in range(0, len(article)):
            highlight_article = []
 
            for j in range(0, len(article[i])):
                highlight_variables = []
                for k in range(0, len(variable_keywords)):
                    highlight_variables.append(random.random())
                highlight_article.append(highlight_variables)
     
            highlight.append(highlight_article)
             
 
 
        return highlight
 
#input: 
#article: two-dimensional array of the article: the first dimension corresponds to the paragraph, second corresponds to sentences. 
#variable_keywords: one-dimenstional array of comma-separated keywords
#variable_pages: array of the page numbers assigned to the variables (index identical to variable_keywords).
#output: three-dimensional array: paragraph-sentence-variables, meaning that for every sentence in a paragraph we have a score for every variable \in [0,1]
    def getHighlightingsVariables(self, article, variable_keywords, variable_pages):
        stemmer = snowballstemmer.stemmer("german")
        for i in range(0, len(article)):
            for j in range(0, len(article[i])):
                article[i][j] = article[i][j].split(" ");
                for k in range(0, len(article[i][j])):
                    #article[i][j][k]=chrtran(article[i][j][k], goodchars, "")
                    article[i][j][k]=stemmer.stemWord(article[i][j][k])
 
 
        for i in range(0, len(variable_keywords)):
            #variable_keywords[i]=chrtran(variable_keywords[i], goodchars, "")
            variable_keywords[i]=stemmer.stemWord(variable_keywords[i])
 
        highlight = []
 
        for i in range(0, len(article)):
            highlight_article = []
     
            for j in range(0, len(article[i])):
                highlight_variables = []
                for k in range(0, len(variable_keywords)):
                    highlight_variables.append(random.random())
                highlight_article.append(highlight_variables)
 
            highlight.append(highlight_article)
             
 
 
        return highlight
 
pass