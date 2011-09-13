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

#from amcat.tools.selection import forms
import amcat.tools.selection.database
import amcat.tools.selection.solrlib
from django.db.models import Min, Max
from amcat.model.medium import Medium
from django.db import connection
import time

import logging
log = logging.getLogger(__name__)
#DISPLAY_IN_MAIN_FORM = 'DisplayInMainForm'




    
class ArticleSetStatistics(object):
    def __init__(self, articleCount=None, firstDate=None, lastDate=None, mediums=[]):
        self.articleCount = articleCount
        self.firstDate = firstDate
        self.lastDate = lastDate
        self.mediums = mediums
    
class WebScript(object):
    name = None # the name of this webscript
    template = None # special markup to display the form
    form = None # fields specific for this webscript
    displayLocation = None # should be (a list of) another WebScript name that is displayed in the main form
    
    def __init__(self, generalForm, ownForm):
        self.generalForm = generalForm
        self.ownForm = ownForm
        self.isIndexSearch = generalForm.cleaned_data['useSolr'] == True
        self.initTime = time.time()
        
    def getStatistics(self):
        form = self.generalForm
        s = ArticleSetStatistics()
        if self.isIndexSearch == False: # make database query
            qs = amcat.tools.selection.database.getQuerySet(**form.cleaned_data)
            s.articleCount = qs.count()
            result = qs.aggregate(firstDate=Min('date'), lastDate=Max('date'))
            s.firstDate = result['firstDate']
            s.lastDate = result['lastDate']
            mediumids = [x['medium_id'] for x in qs.values('medium_id').distinct()]
            s.mediums = sorted(Medium.objects.in_bulk(mediumids).values(), key=lambda x:x.id) # TODO: there must be a more effcient way to get all distinct medium objects...
            #print s.mediums
            
        else:
            amcat.tools.selection.solrlib.getStats(s, form.cleaned_data['query'], amcat.tools.selection.solrlib.createFilters(form.cleaned_data))
            
        return s
        
    def getArticles(self, start=0, length=30, highlight=True):
        """ returns an iterable of articles, when Solr is used, including highlighting """
        form = self.generalForm
        if self.isIndexSearch == False: # make database query
            return amcat.tools.selection.database.getQuerySet(**form.cleaned_data)[start:length].select_related('medium')
        else:
            if highlight:
                return amcat.tools.selection.solrlib.highlight(form.cleaned_data['query'], start=start, length=length, filters=amcat.tools.selection.solrlib.createFilters(form.cleaned_data))
            else:
                return amcat.tools.selection.solrlib.getArticles(form.cleaned_data['query'], start=start, length=length, filters=amcat.tools.selection.solrlib.createFilters(form.cleaned_data))
        
        
        
    
        