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

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # html pages
    url(r'^$', 'annotator.views.overview.index'),
    url(r'^overview$', 'annotator.views.overview.index', name='annotator-overview'),
    url(r'^overview/table$', 'annotator.views.overview.table', name='annotator-overview-table'),
    url(r'^codingjob/(?P<codingjobid>\d+)$', 'annotator.views.codingjob.index', name='annotator-codingjob'),
    
    # rest api stuff
    url(r'^codingjob/(?P<codingjobid>\d+)/fields$', 'annotator.views.codingjob.fields', name='annotator-codingjob-fields'),
    url(r'^codingjob/(?P<codingjobid>\d+)/articles$', 'annotator.views.codingjob.articles', 
            name='annotator-codingjob-articles'),
    url(r'^article/(?P<articleid>\d+)/sentences$', 'annotator.views.codingjob.articleSentences', 
            name='annotator-article-sentences'),
    url(r'^codingjob/(?P<codingjobid>\d+)/article/(?P<articleid>\d+)/articlecodings$', 'annotator.views.codingjob.articleCodings', name='annotator-article-codings'),
    url(r'^codingjob/(?P<codingjobid>\d+)/article/(?P<articleid>\d+)/unitcodings$', 
            'annotator.views.codingjob.unitCodings', name='annotator-unit-codings'),
    url(r'^codingjob/(?P<codingjobid>\d+)/article/(?P<articleid>\d+)/storecodings$', 
            'annotator.views.codingjob.storeCodings', name='annotator-store-codings'),

)
