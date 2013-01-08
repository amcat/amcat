from amcat.models import Codebook

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException

from api.rest.resources.amcatresource import AmCATResource

from django.conf.urls import url

import collections

MAX_CODEBOOKS = 5
CACHE_LABELS = (2, 1)

class CodebookCycleException(APIException):
    pass

def _walk(codebook, children, nodes, seen=None):
    seen = set() if seen is None else seen

    for node in nodes:
        if node in seen:
            # A cycle was detected in this hierarchy.
            raise CodebookCycleException("Cycle? {}".format(node))

        seen.add(node)

        cc = codebook.get_codebookcode(node)
        cc = cc if cc is None else {
            "hide" : cc.hide,
        }

        yield {
            "id" : node.id,
            "label" : node.get_label(*CACHE_LABELS),
            "children" : _walk(codebook, children, children[node], seen),
            "codebook_code" : cc
        }

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

    def _get(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        if len(qs) > MAX_CODEBOOKS:
            yield "Please select at most {} codebook(s)".format(MAX_CODEBOOKS)
        else:
            for codebook in qs:
                # Cache bases and objects thereof
                codebook.cache()

                # Cache all labels
                for lang in CACHE_LABELS:
                    codebook.cache_labels(lang)

                children = collections.defaultdict(set)
                hierarchy = codebook.get_hierarchy(include_hidden=True)
                nodes = codebook.get_roots(include_missing_parents=True, include_hidden=True)

                for child, parent in hierarchy:
                    if parent:
                        children[parent].add(child)

                for node in _walk(codebook, children, nodes):
                    yield node

    def get(self, request, *args, **kwargs):
        return Response(self._get(request, *args, **kwargs))

