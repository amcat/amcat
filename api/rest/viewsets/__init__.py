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
from inspect import isclass
from rest_framework.viewsets import ViewSetMixin

from api.rest.viewset import AmCATViewSetMixin

from api.rest.viewsets.article import *
from api.rest.viewsets.articleset import *
from api.rest.viewsets.coding.codingjob import *
from api.rest.viewsets.coding.codingrule import *
from api.rest.viewsets.coding.coded_article import *
from api.rest.viewsets.coding.coding import *
from api.rest.viewsets.coding.codebook import *
from api.rest.viewsets.coding.codingschema import *
from api.rest.viewsets.coding.codingschemafield import *
#from api.rest.viewsets.sentence import *
from api.rest.viewsets.project import *
from api.rest.viewsets.task import *
from api.rest.viewsets.preprocess import *
from api.rest.viewsets.query import *
from api.rest.viewsets.uploadplugin import *
from api.rest.viewsets.user import *

def get_viewsets():
    for cls in globals().values():
        if isclass(cls) and issubclass(cls, AmCATViewSetMixin) and not cls.__name__.endswith('Mixin'):
            yield cls
