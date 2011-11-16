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
Model module representing ontology Codebooks. Codebooks are hierarchical
collections of codes that can be used as a source of objects to be coded, 
or to derive automatically generated search terms from. 
"""

from __future__ import unicode_literals, print_function, absolute_import

import logging; log = logging.getLogger(__name__)

from django.db import models

from amcat.tools.model import AmcatModel
from amcat.model.coding.code import Code
from amcat.model.project import Project

class Codebook(AmcatModel):
    """Model class for table codebooks"""

    id = models.AutoField(primary_key=True, db_column='codebook_id')

    project = models.ForeignKey(Project)

    name = models.TextField()

    class Meta():
        db_table = 'codebooks'
        app_label = 'amcat'

    def __unicode__(self):
        return self.name
    
    def add_code(self, code, parent=None, hide=False):
        """Add the given code to the hierarchy, with given parent (or hide)"""
        if parent and hide: raise ValueError("Hidden objects cannot specify parent")
        if isinstance(parent, CodebookCode): parent = parent.code
        if isinstance(code, CodebookCode): code = code.code
        return CodebookCode.objects.create(codebook=self, code=code, parent=parent, hide=hide)

    @property
    def bases(self):
        """Return the base codebooks in the right order"""
        for codebookbase in self.codebookbase_set.all():
            yield codebookbase.supercodebook
    
    def get_hierarchy(self):
        """Return a mapping of code, parent pairs that forms the hierarchy of this codebook
        
        A code is in a codebook if (a) it is listed in its direct codebookcodes, or
        (b) if it is in any of the base codebooks and not explicitly hidden in this codebook.
        The parent of a code is its parent in the codebook it came from, ie in this codebook
        if listed, otherwise in the first base that listed it.
        """
        # go through hierarchy sources in reverse order and update result dict
        # so newest overrides oldest
        result = {}
        for base in reversed(list(self.bases)):
            result.update(base.get_hierarchy())
        result.update(dict((co.code, co.parent) for co in
                           self.codebookcodes.filter(hide=False)))
        # Remove 'hide' objects from the result, and return
        for co in self.codebookcodes.filter(hide=True):
            del result[co.code]
        return result

    @property
    def codes(self):
        """Returns the sequence of codes that are in this hierarchy"""
        return self.get_hierarchy().keys()

    def add_base(self, codebook, rank=None):
        """Add the given codebook as a base to this codebook"""
        if rank is None:
            maxrank = self.codebookbase_set.aggregate(models.Max('rank'))['rank__max']
            rank = maxrank+1 if maxrank is not None else 0
        return CodebookBase.objects.create(subcodebook=self, supercodebook=codebook, rank=rank)
    
class CodebookBase(AmcatModel):
    """Many-to-many field (codebook : codebook) with ordering"""
    id = models.AutoField(primary_key=True, db_column='codebook_base_id')
    supercodebook = models.ForeignKey(Codebook, db_index=True, related_name="+")
    subcodebook = models.ForeignKey(Codebook, db_index=True)
    
    rank = models.IntegerField(default=0, null=False)
    
    class Meta():
        db_table = 'codebook_bases'
        app_label = 'amcat'
        ordering = ['rank']
        unique_together = ("supercodebook", "subcodebook")
    
            
class CodebookCode(AmcatModel):
    """Many-to-many field (codebook : code) with additional properties"""
    id = models.AutoField(primary_key=True, db_column='codebook_object_id')
    
    codebook = models.ForeignKey(Codebook, db_index=True, related_name="codebookcodes")
    
    code = models.ForeignKey(Code, db_index=True, related_name="+")
    parent = models.ForeignKey(Code, db_index=True, related_name="+", null=True)

    hide = models.BooleanField(default=False)               
    
    class Meta():
        db_table = 'codebook_codes'
        app_label = 'amcat'
        unique_together = ("codebook", "code")
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodebook(amcattest.PolicyTestCase):
    def test_create(self):
        """Can we create objects?"""
        c = amcattest.create_test_codebook()

        o = amcattest.create_test_code()
        co = c.add_code(o)
        co2 = c.add_code(Code.objects.create(), parent=o)
        
        self.assertIn(co, c.codebookcodes.all())
        #self.assertIn(o, c.codes)
        self.assertEqual(co2.parent, o)


    def test_hierarchy(self):
        """Does the code/parent base class resolution work"""
        def standardize(codebook):
            """return a dense hierarchy serialiseation for easier comparisons"""

            return ";".join(sorted({"{0}:{1}".format(*cp) 
                                    for cp in codebook.get_hierarchy().items()}))

        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]

        # A: a
        #    +b
        #     +c
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b, a)
        A.add_code(c, b)
        self.assertEqual(standardize(A), 'a:None;b:a;c:b')

        # D: d
        #    +e
        #    +f
        D = amcattest.create_test_codebook(name="D")
        D.add_code(d)
        D.add_code(e, d)
        D.add_code(f, d)
        self.assertEqual(standardize(D), 'd:None;e:d;f:d')
        
        # A+D: a
        #      +b
        #       +c
        #      d
        #      +e
        #      +f
        AD = amcattest.create_test_codebook(name="A+D")
        AD.add_base(A)
        AD.add_base(D)
        self.assertEqual(standardize(AD), 'a:None;b:a;c:b;d:None;e:d;f:d')
        # now let's hide c and redefine e to be under b
        AD.add_code(c, hide=True) 
        AD.add_code(e, parent=b)
        self.assertEqual(standardize(AD), 'a:None;b:a;d:None;e:b;f:d')

        # Test precendence between bases
        # B: b
        #    +d
        #    +e
        B = amcattest.create_test_codebook(name="B")
        B.add_code(b)
        B.add_code(d, b)
        B.add_code(e, b)
        self.assertEqual(standardize(B), 'b:None;d:b;e:b')
        # D+B: d     B+D: b
        #      +e         +d
        #      +f          +f
        #      b          +e
        DB = amcattest.create_test_codebook(name="D+B")
        DB.add_base(D)
        DB.add_base(B)
        self.assertEqual(standardize(DB), 'b:None;d:None;e:d;f:d')
        BD = amcattest.create_test_codebook(name="B+D")
        BD.add_base(B)
        BD.add_base(D)
        self.assertEqual(standardize(BD), 'b:None;d:b;e:b;f:d')
        
    def test_unique(self):
        """Test the uniqueness constraints"""
        from django.db import IntegrityError
        A = amcattest.create_test_codebook(name="A")
        B = amcattest.create_test_codebook(name="B")
        A.add_base(B)
        self.assertRaises(IntegrityError, A.add_base, B)
        self.assertRaises(IntegrityError, A.add_base, B)
        c = amcattest.create_test_code()
        A.add_code(c)
        self.assertRaises(IntegrityError, A.add_code, c)
