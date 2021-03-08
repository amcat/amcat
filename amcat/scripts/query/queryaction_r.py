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
"""
This module holds classes which enable R query actions within AmCAT. As of
now 
"""
from json import JSONEncoder

import functools
import json
import os
import re
import logging

from collections import OrderedDict
from threading import Lock

import datetime
from django import forms
from django.db.models import QuerySet, Model
from rest_framework.authtoken.models import Token

from rpy2 import robjects
from rpy2.robjects import r
import rpy2.robjects.packages as rpackages

from amcat.scripts.forms.selection import Filter
from amcat.scripts.query import QueryActionForm, QueryAction
from amcat.scripts.query import QueryActionHandler
from amcat.tools.toolkit import synchronized_with

R_STRING_RE = re.compile(r'^\[1\] "(?P<str>.*)"$', re.DOTALL)
R_DEPENDENCIES = {
    "amcatr": "amcat/amcat-r",
}

def source_r_file(path):
    """Executes a file in R, similar to 'include' in C or import in Python"""
    r('source("{path}")'.format(path=path))


@functools.lru_cache()  # Only run once
def initialize_r():
    """Sets up R environment. Will be called a the end of this module."""
    # set path from which R loads packages and where R stores new packages (install
    # can be called from within R plugins)
    plugindir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'r_plugins'))
    pkgdir = os.path.join(plugindir, 'package_library')
    os.makedirs(pkgdir, exist_ok=True)
    r(".libPaths('{pkgdir}')".format(pkgdir=pkgdir))
    source_r_file(os.path.join(plugindir, 'formfield_functions.r'))

try:
    initialize_r()
except:
    logging.exception("R Initialization failed, R-based query actions might not function")


def install_package(package, upgrade=False, force=False):
    if not upgrade:
        exists = r.suppressPackageStartupMessages(r.require(package))[0]
        if exists:
            print("SKIPPING ", package)
            return
    utils = rpackages.importr('utils')
    utils.chooseCRANmirror(ind=1)
    print("INSTALLING ", package, "; force=", force)
    utils.install_packages(package, force=force)


def _to_r_primitive(obj):
    if isinstance(obj, QuerySet):
        return list(obj.values_list("pk", flat=True))
    elif isinstance(obj, (list, tuple, set)):
        return list(map(_to_r_primitive, obj))
    if isinstance(obj, Model):
        return obj.pk
    return obj


def cleaned_data_to_r_primitives(cdata: dict) -> dict:
    """
    Takes cleaned data (as returned by Django forms) and converts the data into
    suitable types which can be interpreted by R.
    """
    return {k: _to_r_primitive(v) for k, v in cdata.items()}



class RQueryActionHandler(QueryActionHandler):
    pass


class RQueryActionForm(QueryActionForm):
    """

    """
    fieldinfo = None

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

        for label, field in self.fieldinfo.items():
            fieldclass = getattr(forms, field['type'])
            self.fields[label] = fieldclass(**field['arguments'])

class RJsonEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Filter):
            return o.__dict__


class RQueryAction(QueryAction):
    """

    """
    task_handler = RQueryActionHandler
    output_types = (("text/html", "Result"),)

    # Pointing to an r file, relative to amcat/scripts/query/r_plugins
    r_file = None

    @property
    @functools.lru_cache()
    def form_class(self):
        if self.r_file is None:
            raise ValueError("Subclasses must define class attribute r_file.")

        # Include r file, so we can call it later on
        source_r_file(self.r_file)

        # Derive a name of the formclass from the action name
        my_name = self.__class__.__name__
        if my_name.endswith("Action"):
            my_name = my_name[:-6]

        # We use a dynamic approach with type() to give the form a suitable classname
        fieldinfo = json.loads(r("formfields")[0], object_pairs_hook=OrderedDict)
        return type("{}Form".format(my_name), (RQueryActionForm,), {"fieldinfo": fieldinfo})

    @classmethod
    def get_dependencies(cls):
        if cls.r_file is None:
            raise ValueError("Subclasses must define class attribute r_file.")
        source_r_file(cls.r_file)
        return r.dependencies


    @synchronized_with(Lock())  # We only have one R interpreter
    def _run(self, cdata):
        # Execute script using R
        cdata = {k: v for (k, v) in cdata.items() if v is not None}
        json_dump = json.dumps(cdata, indent=4, cls=RJsonEncoder)
        open("/tmp/test.json", "w").write(json_dump)
        r_json_arguments = robjects.StrVector([json_dump])
        r_arguments = rpackages.importr("rjson").fromJSON(r_json_arguments)
        source_r_file(self.r_file)
        result = str(r['do.call']('run', r_arguments)).encode("utf-8").decode("unicode_escape")

        # Interpret results as string
        match = R_STRING_RE.match(result)
        if not match:
            err_msg = "Expected a string as return value from R script. Got: {}"
            raise ValueError(err_msg.format(result))

        return match.groupdict()["str"]

    def run(self, form):
        cleaned_data = cleaned_data_to_r_primitives(form.cleaned_data)

        # We can only create one token per user..
        api_token, created = Token.objects.get_or_create(user=self.user)
        if not created:
            api_token.created = datetime.datetime.now()
            api_token.save()

        cleaned_data["api_token"] = api_token.key
        cleaned_data["api_host"] = self.api_host
        cleaned_data["project"] = self.project.id
        return self._run(cleaned_data)
