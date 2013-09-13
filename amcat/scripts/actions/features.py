#!/usr/bin/python

##########################################################################
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

import logging; log = logging.getLogger(__name__)
from functools import partial

from django import forms

import collections, csv
from amcat.scripts.script import Script
from amcat.tools.amcatsolr import Solr, filters_from_form
from amcat.tools.table.table3 import Table
from amcat.models import ArticleSet

from amcat.nlp.featurestream import featureStream

class Features(Script):
    """
    Get features from articlesets. 
    """

    class options_form(forms.Form):
        articleset = forms.ModelChoiceField(queryset=ArticleSet.objects.all())
        unitlevel = forms.ChoiceField([('article','article'),('paragraph','paragraph'),('sentence','sentence')], initial='article')
        offset = forms.IntegerField(initial=0)
        batchsize = forms.IntegerField(initial = 1000, max_value=2500)
        mindocfreq = forms.IntegerField(initial=0) ## usefull for reducing size of output, but perhaps this problem should be for the user and not the server.
        
        # implement more options later 
        #features_type = forms.ChoiceField(['Stemmed words with POS'])
        #posfilter = forms.MultipleChoiceField

        
    output_type = Table
    
    def run(self, _input=None):
        articleset_id = self.options['articleset'].id
        unit_level = self.options['unitlevel']
        min_docfreq = self.options['mindocfreq']
        offset = self.options['offset']
        batchsize = self.options['batchsize']

        ## implement more options later
        featurestream_parameters = {'posfilter':['noun','NN','verb'], 'zeropunctuation':True}
        f = featureStream(**featurestream_parameters)

        rows = []
        index, index_counter = {}, 1
        docfreq = collections.defaultdict(lambda:0)
        for a,parnr,sentnr,features in f.streamFeaturesPerUnit(articleset_id=articleset_id, unit_level=unit_level, offset=offset, batchsize=batchsize, verbose=True):
            for feature, count in features.iteritems():
                word = feature[0]
                try: pos = feature[1]
                except: pos = None
                if min_docfreq > 1: docfreq[word] += 1
                rows.append({'id':a.id,'paragraph':parnr,'sentence':sentnr,'word':word,'pos':pos, 'hits':count})

        if min_docfreq > 1:
            relevantwords = [word for word in docfreq if docfreq[word] >= min_docfreq]
            rows = [row for row in rows if row['word'] in relevantwords]
               
        if unit_level == 'article': columns = ['id','word','pos','hits']
        if unit_level == 'paragraph': columns = ['id','paragraph','word','pos','hits']
        if unit_level == 'sentence': columns = ['id','paragraph','sentence','word','pos','hits']

        t = Table(rows=rows, columns = columns, cellfunc=dict.get)
        return t
                    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    print result.output()
    
