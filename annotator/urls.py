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

from django.conf.urls import url, include
from annotator.views import codingjob

article_patterns = [
    url(r'save$', codingjob.save),
]

codingjob_patterns = [
    url('^code$', codingjob.index, name="annotator-codingjob"),
    url(r'^codedarticle/(?P<coded_article_id>\d+)/', include(article_patterns)),
]

urlpatterns = [
    url(r"^codingjob/(?P<codingjob_id>\d+)$", codingjob.redirect, name="annotator-codingjob"),
    url(r"projects/(?P<project_id>\d+)/codingjobs/(?P<codingjob_id>\d+)/", include(codingjob_patterns)),
]
