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

from amcat.nlp.featurestream import featureStream, codedFeatureStream, prepareVectors
from django import db

import re, math, collections, itertools, random, pickle

import nltk, nltk.classify.util, nltk.metrics
from nltk.classify import NaiveBayesClassifier
from nltk.classify.scikitlearn import SklearnClassifier # NLTK wrapper for sklearn
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB

class machineLearning():
    def splitUnits(self, units, train_pct=70, shuffle=True):
        """
        splits a list into two lists. 
        """
        if shuffle == True: random.shuffle(units)
        splitn = int(len(units)*(train_pct/100.0))
        trainunits, testunits = units[:splitn], units[splitn:]
        print("train on %d units, test on %d units" % (len(trainunits), len(testunits)))
        return trainunits, testunits

    def thresholded_classify(self, classifier, units, min_prob, unclassified_label='unclassified'):
        """
        Currently disabled. Only works with classifiers that allow .prob_classify.

        Instead of directly classifying, only classifies if the class with the highest probability has a minimum probability of min_prob. Otherwise, un'unclassified_label' is used to classify.
        """
        sets = collections.defaultdict(lambda:set())
        for l in classifier.labels(): sets[l] = set()

        for unit in units:
            a, parnr, sentnr, features = unit[0], unit[1], unit[2], unit[3]
            highest_p = 0
            for l in classifier.labels():
                p = classifier.prob_classify(features).prob(l)
                if p > highest_p: predicted, highest_p = l, p

            if highest_p > min_prob: sets[predicted].add((a,parnr,sentnr))
            else: sets[unclassified_label].add((a,parnr,sentnr))
        return sets

    def classify(self, classifier, units):
        """
        Classifies a list of units based on the prediction of the classifier.
        """
        sets = collections.defaultdict(lambda:set())
        for l in classifier.labels(): sets[l] = set()

        for unit in units:
            a, parnr, sentnr, features = unit[0], unit[1], unit[2], unit[3]
            predicted = classifier.classify(features)
            sets[predicted].add((a,parnr,sentnr))
        return sets

    def getReferenceSets(self, units):
        """
        Classifiers a list of units based on the provided coded values, for comparison with the results of the classifier.
        """
        sets = collections.defaultdict(lambda:set())
        for a, parnr, sentnr, features, label in units:
            sets[label].add((a,parnr,sentnr))
        return sets
                                                     
    def test(self, classifier, testunits):
        """
        Tests and reports the performance of the classifier 
        """
        testsets = self.classify(classifier, testunits)
        refsets = self.getReferenceSets(testunits)

        print('\n%30s   %10s   %10s   %10s   %10s   %10s' % ('N.reference', 'N.test','precision','recall','F-measure', 'prior probability'))
        pr_dict = {}
        all_labels = set(testsets.keys() + refsets.keys())

        for v in all_labels:
            if not v in testsets: testsets[v] = set()
            if not v in refsets: refsets[v] = set()
            if len(str(v)) > 12: vlabel = "%s..." % str(v)[0:12]
            else: vlabel = v
            p = nltk.metrics.precision(refsets[v], testsets[v])
            r = nltk.metrics.recall(refsets[v], testsets[v])
            if p and r:
                f = round((2 * p*r) / (p + r),3)
                p = round(p,3)
                r = round(r,3)
            else: f, p, r = 'NA','NA','NA'
            try: pp = round(classifier.prob_classify({}).prob(v),3)
            except: pp = 'NA'
            n_ref = len(refsets[v])
            n_test = len(testsets[v])
            print('%-20s%10s   %10s   %10s   %10s   %10s   %10s' % (vlabel,n_ref,n_test,p,r,f,pp))
            pr_dict[v] = {'N_reference':n_ref, 'N_test':n_test, 'precision':p, 'recall':r, 'F-measure':f, 'prior_probability':pp}
        print('\n')

        #classifier.show_most_informative_features(10)
        testscores = {'precision_and_recall':pr_dict,'N':len(testunits)}
        return testscores

    def save(self, name, classifier, classifier_meta):
        """
        Save a trained classifier and the classifier_meta, which contains the used parameters and testscores. 
        """
        c_filename = "/tmp/%s.pickle" % name
        cmeta_filename = "/tmp/%s_meta.pickle" % name
        print('\nSAVING CLASSIFIER TO %s AND %s\n' % (c_filename, cmeta_filename))
        f = open(c_filename, 'wb')
        f_meta = open(cmeta_filename, 'wb')
        pickle.dump(classifier, f)
        pickle.dump(classifier_meta, f_meta)
        f.close()
        f_meta.close()
             
    def load(self, name):
        """
        Loads a pre-trained classifier and the classifier_meta
        """
        c_filename = "/tmp/%s.pickle" % name
        cmeta_filename = "/tmp/%s_meta.pickle" % name
        print('\nLOADING CLASSIFIER: %s AND %s' % (c_filename, cmeta_filename))
        f = open(c_filename)
        f_meta = open(cmeta_filename)
        classifier = pickle.load(f)
        classifier_meta = pickle.load(f_meta)
        f.close()
        f_meta.close()
        return classifier, classifier_meta

    def balanceLabelProbabilities(self, classifier):
        """
        Fool a naive bayes classifier into balanced class probabilities. Currently not implemented. 
        """
        fd = FreqDist()
        for l in classifier.labels(): fd.inc(l) # fake a balanced freq distribution of labels
        classifier._label_probdist._freqdist = fd # insert balanced freq distribution into classifier's label/prior probability distribution
        return classifier

    def selectClassifier(self, classifier_type):
        """
        Selects a classifier
        """
        if classifier_type == 'naivebayes': classifier = NaiveBayesClassifier
        if classifier_type == 'multinomialnb': classifier = SklearnClassifier(MultinomialNB())
        if classifier_type == 'linearsvc': classifier = SklearnClassifier(LinearSVC())
        return classifier

    def prepareData(self, codingjob_ids, fieldnr, unit_level, recode_dict=None, featurestream_parameters={}):
        """
        Uses the featurestream module to prepare data from amcat for machinelearning.
        """
        cfs = codedFeatureStream(**featurestream_parameters)
        cfpu = [cf for cf in cfs.streamCodedFeaturesPerUnit(codingjob_ids, fieldnr, unit_level, recode_dict)]
        classifier_meta = {'featurestream_parameters':featurestream_parameters,
                           'trainingcorpus':{'codingjob_ids':codingjob_ids,
                                             'fieldnr':fieldnr,
                                             'unit_level':unit_level,
                                             'recode_dict':recode_dict}}
        random.shuffle(cfpu)
        return cfpu, classifier_meta

    def trainClassifier(self, codedfeaturesperunit, classifier_meta, classifier_type='multinomialnb', vectortransformation='tfidf', featureselection='chi2', features_pct=50, train_pct=80, save_classifier=True, name='unnamed_classifier'):
        """
        Uses the prepared data (codedfeaturesperunit and classifier_meta) to train a classifier.
        """
        pf = prepareVectors()
    
        traincfpu, testcfpu = self.splitUnits(codedfeaturesperunit, train_pct, shuffle=False)
        classifier = self.selectClassifier(classifier_type)

        print('TRAINING')
        arts,parnrs,sentnrs,featureslist,labels = zip(*traincfpu)
        featureslist, selected_features = pf.prepareVectors(featureslist, labels, vectortransformation, featureselection, features_pct)
        trainunits, trainfeatures = zip(arts,parnrs,sentnrs), zip(featureslist,labels)
        print('- training classifier')
        classifier = classifier.train(trainfeatures)

        if train_pct < 100:
            print('TESTING')
            arts,parnrs,sentnrs,featureslist,labels = zip(*testcfpu)
            featureslist, fnames = pf.prepareVectors(featureslist, vectortransformation=vectortransformation, filter_features=selected_features)
            testcfpu = zip(arts,parnrs,sentnrs,featureslist,labels)
            print('- testing classifier')
            testscores = self.test(classifier, testcfpu)
        else: testscores = {}

        if save_classifier == True:
            classifier_meta['trainingcorpus']['trainunits'] = trainunits
            classifier_meta['trainingcorpus']['selected_features'] = selected_features
            classifier_meta['testscores'] = testscores
            classifier_meta['pipeline_parameters'] ={'classifier_type':classifier_type,
                                                     'vectortransformation':vectortransformation,
                                                     'featureselection':featureselection,
                                                     'features_pct':features_pct}
            self.save(name, classifier, classifier_meta)
    

if __name__ == '__main__':
    ## EXAMPLE: predicting whether speaker in parliament is Wilders or Samsom.

    print("----------PREPARE DATA----------\n")
    ml = machineLearning()
    #codingjob_ids = [1395,1396] # large sets
    codingjob_ids = [1453,1454] # small sets
    fieldnr = 10
    unit_level = 'article'
    recode_dict = {0:'Samsom',1:'Wilders'}
    featurestream_parameters = {'headlinefilter':'exclude'} # headline is excluded in this example, because it mentions the name and party of the speaker

    codedfeaturesperunit, classifier_meta = ml.prepareData(codingjob_ids, fieldnr, unit_level, recode_dict, featurestream_parameters)

    print("----------TRAIN AND TEST CLASSIFIERS----------\n")
    # static variables for correct comparison
    train_pct=80 # train on 80 percent of units, test on 20 percent

    print("NAIVE BAYES")
    classifier_type = 'naivebayes'
    vectortransformation = 'binomial'
    featureselection = 'chi2'
    features_pct = 60 # use 60 percent of all features
    save_classifier=True
    name='naivebayes_test'

    ml.trainClassifier(codedfeaturesperunit, classifier_meta,
                    classifier_type, vectortransformation, featureselection, features_pct, train_pct, save_classifier, name)

    print("MULTINOMIAL NAIVE BAYES")
    classifier_type = 'multinomialnb'
    vectortransformation = None # use count
    featureselection = 'chi2'
    features_pct = 60 
    save_classifier=True
    name='multinomialnaivebayes_test'
    
    ml.trainClassifier(codedfeaturesperunit, classifier_meta,
                classifier_type, vectortransformation, featureselection, features_pct, train_pct, save_classifier, name)
    
    print("LINEAR SVC")
    classifier_type = 'linearsvc'
    vectortransformation = 'tfidf' 
    featureselection = 'chi2'
    features_pct = 60 
    save_classifier=True
    name='linearsvc_test'
    
    ml.trainClassifier(codedfeaturesperunit, classifier_meta,
                classifier_type, vectortransformation, featureselection, features_pct, train_pct, save_classifier, name)
