#!/usr/bin/python
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

from __future__ import unicode_literals, print_function, absolute_import

from amcat.models import Article, Coding, Token, Lemma, Word, AnalysedArticle
from amcat.tools.toolkit import clean, stripAccents, RepeatReplacer
from amcat.nlp import sbd
from django import db

import nltk, numpy
import re, math, collections, itertools, random, pickle
from nltk.metrics import BigramAssocMeasures
from nltk.probability import FreqDist, ConditionalFreqDist

from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_selection import SelectKBest, SelectPercentile, chi2

class featureStream():
    """
    A class to iterate through features of articles. Features can be organized on three levels: article, paragraph and sentence. Parsed data can be used (source='parsed'), or raw text (source='rawtext'). For raw text low cost tokenization and stemming options are implemented. Ngrams can be used as well.
    At __init__ the arguments are passed for what features should be used (i.e. words or lemma, strings or id's, ngrams). The 'featurestream' function can then be used to yield these features for a given aricleset and unit level.
    """
    
    def __init__(self, source='rawtext', language='dutch', use_lemma=True, use_id=True, use_stemming=True, remove_repeating=False, delete_stopwords=False, postagging=True, posfilter=None, ngrams=1, lowercase=True, zeropunctuation=False, max_paragraph=None, marknegations=False, headlinefilter=None, reportparameters=True):
        self.source = source
        self.posfilter = posfilter
        self.ngrams = ngrams
        self.postagging = postagging
        self.headlinefilter = headlinefilter
        self.lowercase = lowercase
        self.marknegations = marknegations
        self.zeropunctuation = zeropunctuation
        self.max_paragraph = max_paragraph
        
        if use_stemming == True: self.stemmer = nltk.SnowballStemmer(language)
        else: self.stemmer = None
        if remove_repeating: self.repeatReplacer = RepeatReplacer()
        else: self.repeatReplacer = None
        if delete_stopwords == True: self.stopwords = nltk.corpus.stopwords.words(language)
        else: self.stopwords = None

        if source == 'parsed':
            self.use_lemma = use_lemma
            self.use_id = use_id
            if self.use_id:
                self.repeatReplacer = None
                if self.stopwords:
                    if use_lemma == False: self.stopwords = set(w.id for w in Word.objects.filter(word__in = stopwords))
                    if use_lemma == True: self.stopwords = set(w.id for w in Lemma.objects.filter(lemma__in = stopwords))
       
        if source == 'rawtext':
            self.use_lemma = False
            self.use_id = False
            self.tokenizer = nltk.tokenize.RegexpTokenizer(r'\w+|[^\w\s]+')
            if posfilter or (postagging == True): self.tagger = self.taggerCombo(language)
            
        if reportparameters == True: self.reportParameters()

    def reportParameters(self):
        features = 'words'
        if self.stemmer: features = 'stemmed ' + features
        if self.use_id == False and self.use_lemma == False and self.lowercase == True: features = features + ' (lowercase)'
        if self.use_lemma == True: features = 'lemmata'
        if self.use_id == True: features = features + ' ids'
        if self.postagging == True: features = features + ' with POS tags'
        if self.ngrams > 1: features = features + ', in ngrams of %s' % self.ngrams
        params = ''
        if self.posfilter: params = params + '\n\tOnly used POS tags: %s' % ', '.join(self.posfilter) 
        if self.stopwords: params = params + '\n\tStopwords were ignored'
        if self.marknegations: params = params + '\n\tNegated words were marked'
        if self.repeatReplacer: params = params + '\n\tRepeated characters were removed' 
        print('Features are %s%s\n' % (features, params))

    def taggerCombo(self, language):
        """
        Train (or load) a pos-tagger. A combination of a UnigramTagger, BigramTagger and Trigramtagger is used to train, with 'NN' as a default tag.
        """
        try:
            f = open('/tmp/%s_taggercombo.pickle' % language, 'r')
            tagger = pickle.load(f)
        except:
            if language == 'dutch': traindata = nltk.corpus.alpino.tagged_sents()
            if language == 'english': traindata = nltk.corpus.brown.tagged_sents()
            tagger = nltk.DefaultTagger('NN')
            for taggerclass in [nltk.UnigramTagger, nltk.BigramTagger, nltk.TrigramTagger]:
                tagger = taggerclass(traindata, backoff=tagger)
            f = open('/tmp/%s_taggercombo.pickle' % language, 'w')
            pickle.dump(tagger, f)
        return tagger      

    def getTokensFromDatabase(self, a):
        """
        If articles are preprocessed, this function can yield the tokens of an article as words or lemma, either as strings or id's.
        """
        for t in Token.objects.select_related('sentence__sentence','word__lemma').filter(sentence__analysed_article__id = a.analysedarticle_set.get().id):
            paragraph = t.sentence.sentence.parnr
            sentence = t.sentence.sentence.sentnr
            
            if self.use_id == True:
                if self.use_lemma == True: word = t.word.lemma_id
                else: word = t.word_id
            else:
                if self.use_lemma == True: word = str(t.word.lemma)
                else: word = str(t.word)
            pos = t.word.lemma.pos
            yield (paragraph, sentence, word, pos)

    def getTokensFromRawText(self, a):
        """
        If articles are not parsed, this function gets the raw text, which is then transformed to a list of tokens in self.tokenizeRawText.
        """
        sentences = a.sentences.all()
        if len(sentences) == 0: sentences = sbd.get_or_create_sentences(a)
        for s in sentences:
            paragraph = s.parnr
            sentence = s.sentnr
            for word, pos in self.tokenizeRawText(s.sentence):
                yield (paragraph, sentence, word, pos)

    def tokenizeRawText(self, text):
        """
        Sentences are tokenized (and tagged)
        """
        sent = stripAccents(text)
        if self.zeropunctuation == True: sent = clean(text,25)
        sent = self.tokenizer.tokenize(sent)
        if self.posfilter or (self.postagging == True): tokens = self.tagger.tag(sent)
        else: tokens = [(w, None) for w in sent]
        for word, pos in tokens:
            yield (word, pos)
        
    def getTokens(self, a, unit_level):
        """
        Tokens are extracted from articles.
        """
        if self.source == 'parsed': tokens_per_sentence = self.getTokensFromDatabase(a)
        if self.source == 'rawtext': tokens_per_sentence = self.getTokensFromRawText(a)

        for paragraph, sentence, word, pos in tokens_per_sentence:
            if self.max_paragraph and paragraph > self.max_paragraph: continue
            if self.headlinefilter:
                if self.headlinefilter == 'exclude' and paragraph == 1: continue
                if self.headlinefilter == 'only' and not paragraph == 1: continue
            if unit_level == 'article': paragraph, sentence = None, None # Set levels below unit_level to None
            if unit_level == 'paragraph': sentence = None
            yield (paragraph, sentence, word, pos)

    def getTokensPerUnit(self, a, unit_level):
        """
        Collects Tokens in a list per unit.
        """
        tokens_unit_dict = collections.defaultdict(lambda:[])
        for par, sent, word, pos in self.getTokens(a, unit_level):
            token = (word,pos)
            tokens_unit_dict[(par,sent)].append(token)
        for par, sent in tokens_unit_dict:
            tokens = tokens_unit_dict[(par,sent)]
            yield (par, sent, tokens)

    def prepareFeatures(self, features, as_dict=True):
        """
        Filtering and processing transformations for the features list.
        """
        pf = []
        if self.marknegations: features = self.markNegations(features)
        for feature, pos in self.filterFeatures(features):
            if self.use_id == False: feature = self.processFeature(feature)
            
            if self.postagging == True: pf.append((feature, pos))
            else: pf.append(feature)
        if self.ngrams > 1: pf = self.toNgrams(pf, self.ngrams)
        if as_dict == True: pf = collections.Counter(pf)
        return pf

    def markNegations(self, features):
        """
        Not yet implemented. The idea is to chunk and chink it up, and identify whether words are negated, in which case negated words are marked with 'neg_' and negated id's are made negative (id * -1). Note that this step should occur (as it would now) before filtering stopwords/postags
        """
        return features

    def toNgrams(self, features, ngrams=1):
        """
        Transforms a list of features into a list of ngrams.
        """
        ngram_features = []
        for i in range(0,len(features)):
            feature = features[i]
            if (i+ngrams) > len(features) : break
            for n in range(1,ngrams): feature = "%s_%s" % (feature,features[i+n])
            ngram_features.append(feature)
        return ngram_features
    
    def filterFeatures(self, features):
        for feature, pos in features:
            if self.stopwords and feature in self.stopwords: continue
            if self.posfilter and not pos in self.posfilter: continue
            yield (feature, pos)

    def processFeature(self, feature):
        if self.stemmer: feature = self.stemmer.stem(feature)
        if self.lowercase == True: feature = feature.lower()
        if self.repeatReplacer: feature = self.repeatReplacer.replace(feature)
        return feature

    def getArticles(self, articleset_id, article_ids, offset, batchsize):
        if article_ids: articles = Article.objects.select_related('sentences','analysedarticle_set').filter(pk__in=article_ids)
        else: articles = Article.objects.select_related('sentences','analysedarticle_set').filter(articlesets_set=articleset_id)
        if offset:
            if batchsize:
                batchlimit = offset + batchsize
                articles = articles[offset:batchlimit]
            else: articles = articles[offset:]
        else:
            if batchsize: articles = articles[:batchsize]
        return articles

    def streamFeaturesPerUnit(self, articleset_id=None, article_ids=None, unit_level='sentence', as_dict=True, offset=None, batchsize=None, verbose=True):
        articles = self.getArticles(articleset_id, article_ids, offset, batchsize)
        N = len(articles)
        for i, a in enumerate(articles):
            if verbose == True:
                if i % 2500 == 0: print('\t%s / %s' % (i,N))
            for paragraph, sentence, tokens in self.getTokensPerUnit(a, unit_level):
                features = self.prepareFeatures(tokens, as_dict)
                yield (a, paragraph, sentence, features)


def mean(x): return (sum(x) / float(len(x)))
def mode(x): return collections.Counter(x).most_common(1)[0][0]

class codedFeatureStream(featureStream):
    """
    featureStream for codingjobs, where the values of an assigned coding field are attached to each unit. Meant as a convenience for machinelearning purposes. 
    """
    
    def streamCodedFeaturesPerUnit(self, codingjob_ids, fieldnr, unit_level, recode_dict, aggfunction=mode):
        """
        Extension of streamFeaturesPerUnit, which adds a 'label' object for a coded value. Codingjobs are used as input, and only coded units of this codingjob are returned.
        
        Parameters:
            - codingjob_ids: list of codingjob_ids
            - fieldnr: the nr of the field in the codingschema
            - unit_level: the level at which features are streamed. Can be article, paragraph or sentence. Codings are also gathered from codingjobs at this level, so that at the article level codings from the articleschema are used, and at sentence level the codings from the unitschema. At paragraph level a list of the coded values of sentences is given. At present multiple codings per sentence is not supported.
            - recode_dict: a dictionary to replace coded values (keys) with recoded values (values).
            - aggfunction: if there are multiple codings for a unit -> codingfield, aggregate values
        """
        print('GETTING UNIT CODINGS')
        uc = self.getCodedFields(codingjob_ids=codingjob_ids, fieldnrs=[fieldnr], unit_level=unit_level, aggfunction=aggfunction)
        article_ids = set([aid for aid,parnr,sentnr in uc])

        print('\nYIELDING FEATURES')
        if len(article_ids) == 0: return
        for a, parnr, sentnr, features in self.streamFeaturesPerUnit(article_ids=article_ids, unit_level=unit_level):
            if not (a.id,parnr,sentnr) in uc: continue
            label = uc[(a.id,parnr,sentnr)][fieldnr]
            if recode_dict: label = recode_dict[label]
            yield (a, parnr, sentnr, features, label)
    
    def getCodedFields(self, codingjob_ids, fieldnrs, unit_level=None, aggfunction=None):
        """
        Returns a dictionary where keys are (a.id, parnr, sentnr).
        Values are dictionaries where keys are fieldnrs and values are lists of codings in this field.
        So that the format is: codedfeaturesperunit[(a.id, parnr, sentnr)][fieldnr] = [coding1, coding2, ...]

        Codings are stored in lists, because multiple codings are possible because of multiple coders, and for paragraphs and sentences that allow multiple codings per unit. The aggfunction parameter can be used to aggregate the list to a single value.
        """
        codings_dict = collections.defaultdict(lambda:collections.defaultdict(lambda:[]))

        for codingjob_id in codingjob_ids:
            print("Codingjob: %s" % codingjob_id)
            codings_dict = self.getCodingsFromJob(codingjob_id, fieldnrs, codings_dict, unit_level)
            #print('Queries used: %s' % len(db.connection.queries)) # Perhaps the number of database hits could still be reduced in the c.values selectio
        if aggfunction: codings_dict = self.aggregateCodings(codings_dict, aggfunction)
        return codings_dict

    def aggregateCodings(self, codings_dict, aggfunction):
        agg_cd = collections.defaultdict(lambda:{})
        for unit, codings in codings_dict.iteritems():
            for fieldnr, values in codings.iteritems():
                value = aggfunction(values)
                agg_cd[unit][fieldnr] = value
        return agg_cd

    def getCodingsFromJob(self,codingjob_id, fieldnrs, codings_dict, unit_level=None):
        for c in Coding.objects.select_related('codingjob','article','values').filter(codingjob_id = codingjob_id):
            if unit_level:
                if unit_level in ['paragraph','sentence'] and not c.sentence_id: continue
                if unit_level == 'article' and c.sentence_id: continue
            codings_dict = self.getCodings(c, codings_dict, fieldnrs)
        return codings_dict
    
    def getCodings(self, c, codings_dict, fieldnrs):
        if c.sentence_id: article_id, parnr, sentnr = c.article_id, c.sentence.parnr, c.sentence.sentnr 
        else: article_id, parnr, sentnr = c.article_id, None, None
        
        if fieldnrs: values = [(v.field, v.value) for v in (c.values.select_related('field__fieldnr','value').filter(field__fieldnr__in=fieldnrs))]
        else: values = [(v.field, v.value) for v in (c.values.select_related('field__fieldnr','value'))]
        if len(values) == 0: return codings_dict
        for v in values:
            fieldnr = v[0].fieldnr
            if fieldnr in fieldnrs:
                value = v[1]
                if c.sentence_id: # if sentence coding 
                    codings_dict[(article_id, parnr, sentnr)][fieldnr].append(value) # sentence
                    codings_dict[(article_id, parnr, None)][fieldnr].append(value) # paragraph 
                else:
                    codings_dict[(article_id, None, None)][fieldnr].append(value) # article
        return codings_dict


class binomialTransformer():
    """
    Class to mimic sklearn transformers functionality
    """
    def fit(self, csr_matrix):
        None
    def transform(self, csr_matrix):
        csr_matrix.data = csr_matrix.data * 0 + 1
        return csr_matrix

class prepareVectors():
    """
    Class for vector transformation and feature selection. (Note that it cannot be implemented in featurestream since it requires information of the corpus)
    The transformations are performed using the sklearn package. 
    (currently only chi2 is supported for feature selection. Other options (e.g., freq) can be added) 
    """
    def prepareVectors(self, featureslist, classlist=None, vectortransformation=None, featureselection=None, features_pct=50, returnasmatrix=False, filter_features=None, returnindexed=False):
        """
        Takes a list of dictionaries (representing units), in which keys are words and values their occurence within the unit. Vector can be transformed to tfidf or binomial. Featureselection selects a percentage of the featurelist (features_pct) based on a score for the relevance of the feature (e.g., chi2). Note that for certain feature selection methods (e.g., chi2), a list of class labels to match the units in the featureslist needs to be provided. If filter_features is a list of feature names, only these features are used.

        A tuple is returned with the features (as dictionary or sparse matrix) and a list of the selected features. (these selected features can be used as input for 'filter_features' to match new vectors to the vectors on which a classifier is trained) 
        """
        dv = DictVectorizer()
        fmatrix = dv.fit_transform(featureslist)
        fnames = dv.feature_names_
        if vectortransformation:
            print('- Transforming vectors')
            fmatrix = self.transformVectors(fmatrix, vectortransformation)
        if featureselection and not filter_features:
            print('- Selecting features')
            fmatrix, fnames = self.selectFeatures(fmatrix, fnames, featureselection, classlist, features_pct)
            dv.feature_names_ = fnames # store new index of featurenames for dv.inverse_transform
        if filter_features:
            print('- Filtering features')
            fmatrix, fnames = self.filterFeatures(fmatrix, fnames, filter_features)
            dv.feature_names_ = fnames
        if returnasmatrix == False:
            if returnindexed == True: dv.feature_names_ = range(0,len(fnames))
            return (dv.inverse_transform(fmatrix), fnames)
        else: return (fmatrix, fnames)

    def selectFeatures(self, fmatrix, fnames, method, classlist, features_pct):
        if method == 'chi2': sk = SelectPercentile(chi2, features_pct)
        fmatrix = sk.fit_transform(fmatrix, classlist)
        selectedfeatures = zip(sk.get_support(), fnames)
        fnames = [feature for selected, feature in selectedfeatures if selected == True]
        return (fmatrix, fnames)
  
    def transformVectors(self, fmatrix, vectortransformation):
        if vectortransformation == 'tfidf': transformer = TfidfTransformer()
        if vectortransformation == 'binomial': transformer = binomialTransformer()
        transformer.fit(fmatrix)
        fmatrix = transformer.transform(fmatrix)
        return fmatrix

    def filterFeatures(self, fmatrix, fnames, filter_features):
        matching = set(fnames) & set(filter_features)
        featureindex = {fnames.index(m):m for m in matching}
        fmatrix = fmatrix[:,featureindex.keys()]
        fnames = featureindex.values()
        return (fmatrix, fnames) 
