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
Code to initialize/populate the amcat database
It will load the initial_data file, create the default admin account,
and unhook the interactive auth prompt
"""

import os.path

import logging
log = logging.getLogger(__name__)

from django.db.models.signals import post_syncdb
from django.core.management.commands.loaddata import Command

from django.contrib.auth import models as auth_models
from django.contrib.auth.management import create_superuser
from amcat.models.authorisation import Role
from amcat.models.plugin import PluginType, Plugin

import amcat.models
from amcat.tools import classtools

INITIAL_DATA_MODULE = amcat.models
INITIAL_DATA_FILE = "initial_data.json"

def create_admin():
    """Create the admin account if it doesn't exit"""
    try:
        auth_models.User.objects.get(username='amcat')
    except auth_models.User.DoesNotExist:
        su = auth_models.User.objects.create_superuser('amcat', 'amcat@example.com', 'amcat')
        sup = su.get_profile()
        sup.role = Role.objects.get(label="superadmin", projectlevel=False)
        sup.save()
        print("#"*70)
        print("# A default superuser `amcat` with password `amcat` has been created. #")
        print("#"*70)

def register_plugins():
    log.info("Registering plugins...")
    for pt in PluginType.objects.all():
        if pt.package == "amcat.nlp":
            continue # skip analyses - they need language and can't currently be done automatically
        log.debug("Checking plugins of type {pt}".format(**locals()))
        for cls in pt.get_classes():
            log.debug("Checking plugin {cls}".format(**locals()))
            try:
                Plugin.objects.get(module=cls.__module__, class_name=cls.__name__, type=pt)
            except Plugin.DoesNotExist:
                log.debug("Creating plugin")
                plugin_module = amcat.tools.classtools.import_attribute(cls.__module__)
                Plugin.objects.create(module=cls.__module__, class_name=cls.__name__, type=pt,
                                      label=cls.__name__, description=plugin_module.__doc__.strip())
    
        
def initialize(sender, **kwargs):
    """
    Initialize the amcat database by loading data and creating the admin account
    """
    datafile = os.path.join(os.path.dirname(amcat.models.__file__), "initial_data.json")
    Command().run_from_argv(["manage", "loaddata", datafile])
    create_admin()
    register_plugins()

def set_signals():
    """
    Add load_data to amcat.models::post_syncdb to make sure data is loaded before
    auth, and unhook the django.auth create_superuser hook
    """
    post_syncdb.connect(initialize, sender=amcat.models)
    # From http://stackoverflow.com/questions/1466827/ --
    post_syncdb.disconnect(
        create_superuser,
        sender=auth_models,
        dispatch_uid='django.contrib.auth.management.create_superuser'
        )
