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
        unit_level = forms.CharField()
        offset = forms.IntegerField()
        batchsize = forms.IntegerField()
        min_docfreq = forms.IntegerField(initial=0) ## usefull for reducing size of output, but perhaps this problem should be for the user and not the server.
    output_type = Table
    
    def run(self, _input=None):
        articleset_id = self.options['articleset'].id
        unit_level = self.options['unit_level']
        min_docfreq = self.options['min_docfreq']
        offset = self.options['offset']
        batchsize = self.options['batchsize']
        
        featurestream_parameters = {'delete_stopwords':True, 'posfilter':['noun','NN','verb']}
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
        else: columns = ['id',unit_level,'word','pos','hits']

        filename = 'features_set%s_offset%s_batchsize%s.csv' % (articleset_id,offset,batchsize)
        w = csv.writer(open(filename, 'w'))
        for nr, line in enumerate(rows):
            if nr == 0: line = [c for c in columns]
            else: line = [line[c] for c in columns]
            w.writerow(line)
        
        #t = Table(rows=rows, columns = columns, cellfunc=dict.get)
        #return t

    def index(self, word, pos, index={}, index_counter=1):
        """
        Currently not used.
        Indexing saves memory, but perhaps it is better to work in smaller batches using 'offset' and 'batchsize', in which case indexing has less memory to save, and increases processing time, thereby using memory busy for longer.
        """
        if not word in index:
            index[word] = index_counter
            index_counter += 1
        if pos:
            if not pos in index:
                index[pos] = index_counter
                index_counter += 1
        word = index[word]
        if pos: pos = index[pos]
        return (word, pos, index, index_counter)
                    
if __name__ == '__main__':
    from amcat.scripts.tools import cli
    result = cli.run_cli()
    #print result.output()
    
