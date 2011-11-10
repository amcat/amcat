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
Useful functions for dealing with django (models)x
"""

from __future__ import unicode_literals, print_function, absolute_import

from django.db.models import get_model
from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField
from contextlib import contextmanager
import logging; LOG = logging.getLogger(__name__)

def get_related(appmodel):
    """Get a sequence of model classes related to the given model class"""
    # from modelviz.py:222 vv
    for field in appmodel._meta.fields:
        if isinstance(field, (ForeignKey, OneToOneField)):
            yield field.related.parent_model
    if appmodel._meta.many_to_many:
        for field in appmodel._meta.many_to_many:
            if isinstance(field, ManyToManyField) and getattr(field, 'creates_table', False):
                yield field.related.parent_model

def get_all_related(models):
    """Get all related model classes from the given model classes"""
    for m in models:
        for m2 in get_related(m):
            yield m2

def get_related_models(modelnames, stoplist=set(), applabel='amcat'):
    """Get related models

    Finds all models reachable from the given model in the graph of
    (foreign key) relations. If stoplist is given, don't consider edges
    from these nodes.
    
    @type modelname: str
    @param modelname: the name of the model to start from
    @type stoplist: sequence of str
    @param stoplist: models whose children we don't care about
    @return: sequence of model classes
    """
    models = set([get_model(applabel, modelname) for modelname in modelnames])
    stops = set([get_model(applabel, stop) for stop in stoplist])
    while True:
        related = set(get_all_related(models - stops)) # seed from non-stop models
        new = related - models
        if not new: return models
        models |= new
        



@contextmanager   
def list_queries(dest=None):
    """Context manager to print django queries

    Any queries that were used in the context are placed in dest,
    which is also yielded.
    Note: this will set settings.DEBUG to True temporarily.
    """
    if dest is None: dest = []
    from django.conf import settings
    from django.db import connection
    nqueries = len(connection.queries)
    debug_old_value = settings.DEBUG
    settings.DEBUG = True
    try:
        yield dest
        dest += connection.queries[nqueries:]
    finally:
        settings.DEBUG = debug_old_value
        
        
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestDjangoToolkit(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = 'W0212', # use protected _meta
    def test_related_models(self):
        """Test get_related_models function. Note: depends on the actual amcat model"""
        
        for start, stoplist, result in [
            (('Project',), (), ['Affiliation', 'Language', 'Project', 'Role', 'User']),
            (('Sentence',), ('Project',), ['Article', 'Language', 'Medium', 'Project', 'Sentence']),
            ]:
            
            related = get_related_models(start, stoplist)
            related_names = set(r.__name__ for r in related)
            self.assertEqual(related_names, set(result))
            
    def test_queries(self):
        """Test the list_queries context manager"""
        with list_queries() as l:
            amcattest.create_test_user()
        self.assertEqual(len(l), 3) # get affiliation, create user, select user
