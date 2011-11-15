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
Model module representing ontology Codebooks
"""

from __future__ import unicode_literals, print_function, absolute_import

import logging; log = logging.getLogger(__name__)

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.model.ontology.code import Code
from amcat.model.project import Project

class Codebook(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='codebook_id')

    bases = models.ManyToManyField("amcat.Codebook", db_table="codebooks_bases")
    project = models.ForeignKey(Project)

    name = models.TextField()

    class Meta():
        db_table = 'codebooks'
        app_label = 'amcat'

    def __unicode__(self):
        return self.name
    
    def add_code(self, code, parent=None, hide=False):
        if parent and hide: raise ValueError("Hidden objects cannot specify parent")
        if isinstance(parent, CodebookCode): parent = parent.code
        if isinstance(code, CodebookCode): code = code.code
        return CodebookCode.objects.create(codebook=self, code=code, parent=parent, hide=hide)

    @property
    def get_hierarchy(self):
        """Return a mapping of code, parent pairs that forms the hierarchy of this codebook
        
        A code is in a codebook if (a) it is listed in its direct codebookcodes, or
        (b) if it is in any of the base codebooks and not explicitly hidden in this codebook.
        The parent of a code is its parent in the codebook it came from, ie in this codebook
        if listed, otherwise in the first base that listed it.
        """
        hide = set(self.codebookcodes.filter(hide=True))
        result = dict((co.code, co.parent) for co in
                      self.codebookcodes.filter(hide=False))
        return result
    
            
class CodebookCode(AmcatModel):
    id = models.AutoField(primary_key=True, db_column='codebook_object_id')
    
    codebook = models.ForeignKey(Codebook, db_index=True, related_name="codebookcodes")
    
    code = models.ForeignKey(Code, db_index=True, related_name="+")
    parent = models.ForeignKey(Code, db_index=True, related_name="+",null=True)

    hide = models.BooleanField(default=False)               
    
    class Meta():
        db_table = 'codebook_codes'
        app_label = 'amcat'
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodebook(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create objects?"""
        p = amcattest.create_test_project()
        c = Codebook.objects.create(project=p, name="Test")

        o = Code.objects.create()
        co = c.add_code(o)
        co2 = c.add_code(Code.objects.create(), parent=o)
        
        self.assertIn(co, c.codebookcodes.all())
        #self.assertIn(o, c.codes)
        self.assertEqual(co2.parent, o)


    def test_hierarchy(self):
        """Does the code/parent base class resolution work"""
        # simple case: one hierarchy
        p = amcattest.create_test_project()
        A = Codebook.objects.create(project=p, name="Test")

        
