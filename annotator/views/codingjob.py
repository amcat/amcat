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
    

def articleCodings(request, codingjobid, articleid):
    """returns the article codings of an article as HTML form"""
    article = Article.objects.get(id=articleid)
    codingjob = CodingJob.objects.get(id=codingjobid)
    codings = codingtoolkit.get_article_coding(codingjob, article)

    if codings:
        values = codings.get_values()
        values = dict(('field_%s' % field.id, value) for field, value in values)
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
    # Prevent querying the database lots of times
    _function_cache = {}
    def get_function(id):
        if id not in _function_cache:
            _function_cache[id] = Function.objects.get(id=id)
        return _function_cache[id]

    result = []
    if not field.serialiser.possible_values:
        return result

    for val in field.serialiser.possible_values:
        value = field.serialiser.serialise(val)
        label = field.serialiser.value_label(val, language)
        valueDict = dict(label=label, value=value)
        if type(val) == Code: # hack approved by wouter
            functions = []
            for cc in field.codebook.get_codebookcodes(val):
                if cc.function_id != 0:
                    functions.append({'from':cc.validfrom, 'to':cc.validto,
                                      'function':get_function(cc.function_id).label,
                                      'parentid':cc._parent_id})
            if functions:
                valueDict['functions'] = functions
        result.append(valueDict)
    return result

def _show_all(field):
    return None

def _is_ontology(field):
    return (unicode(field.fieldtype) == 'DB ontology')

def _build_field(field, language):
    """
    Returns serialized field
    """
    _res = {
        'fieldname' : field.label,
        'id' : str(field.id),
        'isOntology' : _is_ontology(field),
        'showAll' : _show_all(field)
    }

    if field.codebook:
        _res['items-key'] = field.codebook_id
    else:
        _res['items'] = getFieldItems(field, language)

    return _res

def _build_fields(fields, language):
    """
    Returns serialized fields as iterable
    """
    return (_build_field(f, language) for f in fields)

def _get_functions(code, codebook):
    """
    Return functions belonging to given code
    """
    for cc in code.codebook_codes.all():
        if not cc.function_id:
            continue

        yield {
            "from" : cc.validfrom, "to" : cc.validto,
            "function" : cc.function.label,
            "parentid" : cc._parent_id
        }

        if not (cc.validfrom or cc.validto):
            break

def _get_label(code, language):
    """
    Get label for code for given language.
    """
    for label in code.labels.all():
        if label.language == language:
            return label
    
    return code.labels.all()[0]

def _build_ontology(field, language):
    distinct = ("pk",) if db_supports_distinct_on() else ()

    codes = Code.objects.distinct(*distinct).prefetch_related(
        "labels", "labels__language", "codebook_codes",
        "codebook_codes__function"
    ).filter(
        id__in=field.codebook.get_code_ids()
    )

    return ({
        "value" : code.id,
        "label" : _get_label(code, language).label,
        "functions" : tuple(_get_functions(code, field.codebook))
    } for code in codes)

def _build_ontologies(fields, language):
    ontids = { f.codebook_id for f in fields if f.codebook }

    for field in fields:
        # Do not process same ontology twice
        if not field.codebook_id in ontids:
            continue

        ontids.remove(field.codebook_id)

        yield (field.codebook_id, list(_build_ontology(field, language)))

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

    out = DictToJson().run({
        'fields' : tuple(_build_fields(fields, language)),
        'ontologies':dict(_build_ontologies(fields, language))
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
