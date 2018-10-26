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

"""
Resources in the AmCAT REST API
You can 'register' a resource by adding the model name in the MODELS list
If you want to customize the model, create it in this package and import it here
"""

import sys
from amcat.tools import classtools
from api.rest.resources.amcatresource import AmCATResource
from api.rest.resources.project import ProjectResource
from api.rest.resources.user import UserResource
from api.rest.resources.codebook import CodebookHierarchyResource, CodebookResource, LabelResource
from api.rest.resources.article import ArticleMetaResource, ArticleResource
from api.rest.resources.articleset import ArticleSetResource
from api.rest.resources.codingjob import CodingJobResource
from api.rest.resources.codingrule import CodingRuleResource
from api.rest.resources.coded_article import CodedArticleResource
from api.rest.resources.search import SearchResource
from api.rest.resources.aggregate import AggregateResource
from api.rest.resources.upload import UploadResource
from api.rest.resources.task import single_task_result, TaskResource, TaskResultResource
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from collections import OrderedDict
from logging import getLogger

log = getLogger(__name__)

MODELS = ['AmCAT',
          'Role', 'ProjectRole',
          'Language',
          'CodingSchema', 'CodingSchemaField',
          'CodebookCode', 'CodingSchemaFieldType', 'CodedArticleStatus',
          'django.contrib.auth.models.Group', 'django.contrib.auth.models.Permission',
          "CodingRuleAction",
          "Query"]

# Automatically generate resources for these models
for modelname in MODELS:
    if "." in modelname:
        package, modelname = modelname.rsplit(".", 1)
    else:
        package, modelname = "amcat.models", modelname
    model = classtools.import_attribute(package, modelname)
    resource = AmCATResource.create_subclass(model)
    setattr(sys.modules[__name__], resource.__name__, resource)


def all_resources():
    for r in globals().values():
        if isinstance(r, type) and issubclass(r, AmCATResource) and r != AmCATResource:
            yield r


def get_resource_for_model(model):
    for resource in all_resources():
        if resource.model == model:
            return resource
    log.debug("No resource registered for model {model}".format(**locals()))
    return None


def get_all_resource_views(request):
    for r in all_resources():
        if hasattr(r, "get_model_name"):
            yield (r.get_model_name(), reverse("api:" + r.get_view_name(), request=request))


@api_view(['GET'])
def api_root(request, format=None):
    """
    Overview of API resources
    """
    return Response(OrderedDict(sorted(
        get_all_resource_views(request), key=lambda r: r[0])
    ))
