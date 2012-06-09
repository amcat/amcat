
import os.path

from django.db.models.signals import post_syncdb
from django.core.management.commands.loaddata import Command

import amcat.models

INITIAL_DATA_MODULE = amcat.models
INITIAL_DATA_FILE = "initial_data.json"


def load_data(sender, **kwargs):
    datafile = os.path.join(os.path.dirname(amcat.models.__file__), "initial_data.json")
    Command().run_from_argv(["manage", "loaddata", datafile])

def set_postsync():
    """
    Add load_data to amcat.models::post_syncdb to make sure data is loaded before
    auth 
    """
    post_syncdb.connect(load_data, sender=amcat.models)

    
