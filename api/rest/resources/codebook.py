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

from amcat.models import Codebook

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from api.rest.resources.amcatresource import AmCATResource

from django.conf.urls import url

import collections
import itertools

from amcat.models.coding.codebook import CACHE_LABELS

MAX_CODEBOOKS = 5

class CodebookHierarchyResource(AmCATResource):
    """
    This resource has no direct relationship to one model. Instead, it's
    composed of multiple codebooks. A thorough documentation of the design
    of these hierarchies is available on the AmCAT wiki:

     - https://code.google.com/p/amcat/wiki/Codebook

    Any filters applied to this resource translate directly to filters on
    codebooks. For example, you could request the hierarchy of codebook
    with id '5' using the following query:

     - /codebookhierarchy?id=5

    Two special filters can be applied to hierarchies:

     - include_missing_parents
     - include_hidden

    Each filter displayed above can either be true or false and do not
    rely on each other. Both default to true.
    """
    # ^ Docstring displayed on API web-page as documentation
    model = Codebook

    @classmethod
    def get_url_pattern(cls):
        """The url pattern for use in the django urls routing table"""
        pattern = r'^{}$'.format(cls.get_view_name())
        return url(pattern, cls.as_view(), name=cls.get_view_name())

    @classmethod
    def get_view_name(cls):
        return cls.__name__[:-8].lower()

    @classmethod
    def get_model_name(cls):
        return "codebookhierarchy"

    @classmethod
    def get_tree(cls, codebook, include_labels=True, **kwargs):
        """Codebook.get_tree() with caching enabled"""
        codebook.cache()

        if include_labels:
            for lang in CACHE_LABELS:
                codebook.cache_labels(lang)

        return codebook.get_tree(include_labels=include_labels, **kwargs)

    def _get(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        if len(qs) > MAX_CODEBOOKS:
            return ("Please select at most {} codebook(s)".format(MAX_CODEBOOKS),)
        else:
            return itertools.chain.from_iterable(self.get_tree(codebook) for codebook in qs)

    def get(self, request, *args, **kwargs):
        return Response(self._get(request, *args, **kwargs))


class CodebookResource(AmCATResource):
    model = Codebook
    extra_filters = ["codingschemafield__codingschema__id"]

