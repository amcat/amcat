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

import collections

from django.shortcuts import render

from amcat.models.coding import codingtoolkit
from amcat.models import Code, Coding, CodingJob, CodedArticle
from amcat.models import Function, CodingSchemaField
from amcat.models import Article, Sentence

from django import forms
from django.db.models import Q
from django.http import HttpResponse
from django.utils import simplejson
from django.template.loader import render_to_string

from amcat.scripts.output.datatables import TableToDatatable
from amcat.scripts.output.json import DictToJson, TableToJson
from amcat.forms import InvalidFormException
from amcat.tools.djangotoolkit import db_supports_distinct_on

from itertools import chain

import logging; log = logging.getLogger(__name__)

def index(request, codingjobid):
    """returns the HTML for the main annotator page"""
    return render(request, "annotator/codingjob.html", {'codingjob':CodingJob.objects.get(id=codingjobid), 
        'codingStatusCommentForm':codingtoolkit.CodingStatusCommentForm(auto_id='article-%s')})
    
def writeResponse(data):
    """helper function that returns (binary/text) data as HttpResponse"""
    response = HttpResponse(mimetype='text/plain')
    response.write(data)
    return response
 
    
def articles(request, codingjobid):
    """returns articles in a codingjob as DataTable JSON"""
    table = codingtoolkit.get_table_articles_per_job(
        CodingJob.objects.get(id=codingjobid)
    )
    out = TableToDatatable().run(table)
    return writeResponse(out)
    
   
def unitCodings(request, codingjobid, articleid):
    """returns the unit codings of an article and the HTML form (a row in a table) wrapped in JSON"""
    article = Article.objects.get(id=articleid)
    codingjob = CodingJob.objects.get(id=codingjobid)
    codedArticle = CodedArticle(codingjob, article)
    table = codingtoolkit.get_table_sentence_codings_article(codedArticle, request.user.get_profile().language)
    
    log.info('language: %s' % request.user.get_profile().language)
    
    sentenceform = codingtoolkit.CodingSchemaForm(codingjob.unitschema)
    
    jsondict = {'unitcodings':table, 
                'unitcodingFormTablerow':
                    render_to_string("annotator/unitcodingrowform.html", {'form':sentenceform})
               }
    out = DictToJson().run(jsondict)
    return writeResponse(out)
    

def get_value_labels(coding):
    """
    return a sequence of ('field_{field.id}', value_label) pairs for the given coding.
    If the field is not coded or cannot be deserialized (e.g. because of a codebook change)
    the label '' will be returned.
    """
    for val in coding.values.select_related("field__fieldtype", "value__strval", "value__intval"):
        try:
            value = val.value
        except Code.DoesNotExist: # codebook change
            value = None
        f = val.field
        if value is None:
            label = ''
        else:
            label = f.serialiser.value_label(value)
        yield f, label

def articleCodings(request, codingjobid, articleid):
    """returns the article codings of an article as HTML form"""
    article = Article.objects.get(id=articleid)
    codingjob = CodingJob.objects.get(id=codingjobid)
    codings = codingtoolkit.get_article_coding(codingjob, article)

    if codings:
        values = {"field_%i" % f.id : label for (f, label) in get_value_labels(codings)}
    else:
        values = {}
    articlecodingform = codingtoolkit.CodingSchemaForm(codingjob.articleschema, values)
    
    return render(request, "annotator/articlecodingform.html", {'form':articlecodingform})
    

def articleSentences(request, articleid):
    """returns the sentences found in an article"""
    article = Article.objects.get(id=articleid)
    
    sentences = []
    for s in article.sentences.order_by('parnr', 'sentnr').all():
        sentences.append({'id':s.id, 'unit':'%s.%s' % (s.parnr, s.sentnr), 'text':unicode(s)})
        
    result = {
        'articleid':articleid,
        'sentences':sentences
    }
    
    out = DictToJson().run(result)
    return writeResponse(out)
        
        
def getFieldItems(field, language):
    """get the codebook codes as dictionaries wrapped in a list"""
    if field.serialiser.possible_values:
        for val in field.serialiser.possible_values:
            value = field.serialiser.serialise(val)
            label = field.serialiser.value_label(val, language)
            valueDict = dict(label=label, value=value)

            # hack approved by wouter
            if type(val) == Code:
                functions = _get_functions(val)
                if functions:
                    valueDict['functions'] = [f for f in functions if f.id != 0]

            yield valueDict

def _build_field(field, language):
    result = {
        'fieldname' : field.label,
        'id' : str(field.id),
        'isOntology' : (unicode(field.fieldtype) == 'DB ontology'),
        'showAll' : None
    }

    if field.codebook:
        result['items-key'] = field.codebook_id
    else:
        result['items'] = list(getFieldItems(field, language))

    return result

def _get_functions(codebook, code):
    return [{
        "from" : cc.validfrom, "to" : cc.validto,
        "function" : cc.function.label,
        "parentid" : cc.parent_id
    } for cc in codebook.get_codebookcodes(code)]

def _build_ontology(codebook, language):
    return [{
        "value" : code.id,
        "label" : code.get_label(language),
        "functions" : _get_functions(codebook, code),
    } for code in codebook.get_codes()]

def fields(request, codingjobid):
    """get the fields of the articleschema and unitschema as JSON"""
    language = request.user.get_profile().language
    codingjob = CodingJob.objects.get(id=codingjobid)

    # Get all relevant fields for this codingjob in one query
    fields = CodingSchemaField.objects.select_related(
        # Fields used later in _build_fields and _build_ontologies
        "codebook", "fieldtype", "codingschema"
    ).filter(
        Q(codingschema__codingjobs_unit=codingjob)|
        Q(codingschema__codingjobs_article=codingjob)
    )

    # Make sure all codebooks are the same object
    schemas = set([f.codingschema for f in fields])
    codebooks = { f.codebook.id : f.codebook for f in fields if f.codebook }
    highlighters = set(chain.from_iterable(schema.highlighters.all() for schema in schemas))

    for schema in set([f.codingschema for f in fields]):
        for highlighter in schema.highlighters.all():
            if highlighter.id in codebooks: continue
            codebooks[highlighter.id] = highlighter
        
    for field in (f for f in fields if f.codebook):
        field._codebook_cache = codebooks[field.codebook_id]

    # Cache all codebooks
    for codebook in codebooks.values():
        codebook.cache(select_related=("function",))
        codebook.cache_labels()

    out = DictToJson().run({
        'fields' : [_build_field(f, language) for f in fields],
        'ontologies': {cb.id : _build_ontology(cb, language) for cb in codebooks.values()},
        'highlighters' : [cb.id for cb in codebooks.values() if cb in highlighters]
    })

    return writeResponse(out)
    
    
def updateCoding(fields, form, codingObj):
    """store the form with fields in the codingObj"""
    valuesDict = {}
    for field in fields:
        data = form.cleaned_data['field_%d' % field.id]
        if isinstance(data, int) or data.isdigit(): data = int(data)
        if data == '': continue
        valuesDict[field] = field.serialiser.deserialise(data)
    log.info(valuesDict)
    codingObj.update_values(valuesDict)
    
    
def storeCodings(request, codingjobid, articleid):
    """store the POST data as coding"""
    article = Article.objects.get(id=articleid)
    codingjob = CodingJob.objects.get(id=codingjobid)
    codedArticle = CodedArticle(codingjob, article)
    sentenceMappingDict = {}
    
    try:
        jsonData = simplejson.loads(request.raw_post_data)
        
        log.info(jsonData)
        articleCodingObj = codedArticle.get_or_create_coding()

        if 'articlecodings' in jsonData:
            articlecodingform = codingtoolkit.CodingSchemaForm(codingjob.articleschema, jsonData['articlecodings'])
            
            if not articlecodingform.is_valid():
                raise InvalidFormException('articlecodings', articlecodingform.errors)
            
            updateCoding(codingjob.articleschema.fields.all(), articlecodingform, articleCodingObj)
            
        if 'unitcodings' in jsonData:
            
            for codingdict in jsonData['unitcodings']['modify']:
                unitcodingform = codingtoolkit.CodingSchemaForm(codingjob.unitschema, codingdict)
                
                if not unitcodingform.is_valid() or not codingdict['unit']: # TODO: better unit validation, now unit errors are not in the errors dict (maybe add to form)
                    raise InvalidFormException(codingdict['codingid'], unitcodingform.errors)
                
                unitCodingObj = Coding.objects.get(pk=codingdict['codingid'])
                if unitCodingObj.sentence_id != codingdict['unit']:
                    unitCodingObj.sentence = Sentence.objects.get(pk=codingdict['unit'])
                    unitCodingObj.save()
                updateCoding(codingjob.unitschema.fields.all(), unitcodingform, unitCodingObj)
        
            for codingdict in jsonData['unitcodings']['new']:
                unitcodingform = codingtoolkit.CodingSchemaForm(codingjob.unitschema, codingdict)
                
                if not unitcodingform.is_valid() or not codingdict['unit']: # TODO: better unit validation
                    raise InvalidFormException(codingdict['codingid'], unitcodingform.errors)
                
                sentence = Sentence.objects.get(pk=codingdict['unit'])
                unitCodingObj = codedArticle.create_sentence_coding(sentence)
                updateCoding(codingjob.unitschema.fields.all(), unitcodingform, unitCodingObj)
                sentenceMappingDict[codingdict['codingid']] = unitCodingObj.id
        
            for coding_id in jsonData['unitcodings']['delete']:
                unitCodingObj = Coding.objects.get(pk=coding_id)
                unitCodingObj.delete()
        
        if 'commentAndStatus' in jsonData:
            form = codingtoolkit.CodingStatusCommentForm(jsonData['commentAndStatus'])
            
            if not form.is_valid():
                raise InvalidFormException('commentAndStatus', form.errors)
            
            articleCodingObj.comments = form.cleaned_data['comment']
            articleCodingObj.status = form.cleaned_data['status']
            articleCodingObj.save()
            
            
    except InvalidFormException, e:
        log.exception('form error')
        out = DictToJson().run({'response':'error', 'fields':e.getErrorDict(), 'id':e.message})
    except Exception, e:
        log.exception('store error')
        out = DictToJson().run({'response':'error', 'message':e.message})
    else:
        out = DictToJson().run({'response':'ok', 'codedsentenceMapping':sentenceMappingDict})
    return writeResponse(out)
