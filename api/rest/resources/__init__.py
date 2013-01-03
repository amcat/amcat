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


import types, sys
from amcat.tools import classtools
from api.rest.resources.amcatresource import AmCATResource
from api.rest.resources.project import ProjectResource
from api.rest.resources.user import UserResource


MODELS = ['Article', 'ArticleSet', 
          'Role', 'ProjectRole',
          'Medium', 'Language',
          'CodingJob', 'CodingSchema', 'Codebook', 
          'django.contrib.auth.models.Group', 'django.contrib.auth.models.Permission'
          ]
# Automatically generate resources for these models
for modelname in MODELS:
    if "." in modelname:
        package, modelname = modelname.rsplit(".", 1) 
    else:
        package, modelname = "amcat.models", modelname
    model = classtools.import_attribute(package, modelname)
    resource =  AmCATResource.create_subclass(model)
    setattr(sys.modules[__name__], resource.__name__, resource)

def all_resources():
    for r in globals().values():
        if (isinstance(r, (type, types.ClassType))
            and issubclass(r, AmCATResource)
            and r != AmCATResource):
            yield r

def get_resource_for_model(model):
    for resource in all_resources():
        if resource.model == model:
            return resource
    raise ValueError("No resource registered for model {model}".format(**locals()))


