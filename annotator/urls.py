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

from django.conf.urls import patterns, url, include
from annotator.views import codingjob, overview

article_patterns = patterns('',
    url(r'^sentences$', codingjob.articleSentences, name='annotator-article-sentences'),
    url(r'^articlecodings$', codingjob.articleCodings, name='annotator-article-codings'),
    url(r'^unitcodings$', codingjob.unitCodings, name='annotator-unit-codings'),
    url(r'^storecodings$', codingjob.storeCodings, name='annotator-store-codings'),
)

codingjob_patterns = patterns('',
    url('^$', codingjob.index),

    url(r'^fields$', codingjob.fields, name='annotator-codingjob-fields'),
    url(r'^articles$', codingjob.articles, name='annotator-codingjob-articles'),
    url(r'^article/(?P<article_id>\d+)/', include(article_patterns)),
)

urlpatterns = patterns('',
    url(r'^$', overview.index),
    url(r'^overview$', overview.index, name='annotator-overview'),
    url(r"^codingjob/(?P<codingjob_id>\d+)$", codingjob.redirect, name="annotator-codingjob"),
    url(r"project/(?P<project_id>\d+)/codingjob/(?P<codingjob_id>\d+)/", include(codingjob_patterns)),
)
