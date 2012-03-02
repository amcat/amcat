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
from datetime import datetime

        
from django.db import models

from amcat.tools.model import AmcatModel
from amcat.tools.caching import cached, invalidates
from amcat.models.coding.code import Code, Label

# Setup thread-local cache for codebooks
import threading
_local_cache = threading.local()

def get_codebook(codebook_id):
    """Create the codebook with the given id, possibly retrieving it
    from cache"""
    try:
        books = _local_cache.codebooks
    except AttributeError:
        _local_cache.codebooks = {}
        books = _local_cache.codebooks
    try:
        return books[codebook_id]
    except KeyError:
        books[codebook_id] = Codebook.objects.get(pk=codebook_id)
        return books[codebook_id]

def clear_codebook_cache():
    """Clear the local codebook cache manually, ie in between test runs"""
    _local_cache.codebooks = {}
    

class Codebook(AmcatModel):
    """Model class for table codebooks

    Codebook caches values, so please use the provided methods to add or remove
    objects and bases or call the reset() method after changing them manually.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='codebook_id')
    project = models.ForeignKey("amcat.Project")
    name = models.TextField()

    class Meta():
        ordering = ['name']
        db_table = 'codebooks'
        app_label = 'amcat'

    @property
    @cached
    def bases(self):
        """Return the base codebooks in the right order"""
        return [get_codebook(codebookbase.supercodebook_id)
                for codebookbase in self.codebookbase_set.all()]

    @property
    @cached
    def codebookcodes(self):
        """Return a list of codebookcodes with code and parent prefetched.
        This functions mainly to provide caching for the codebook codes"""
        return list(self.codebookcode_set.select_related("code", "parent"))
    
    def get_codebookcodes(self, code):
        """Return a sequence of codebookcode objects for this code in the codebook

        Iterate over own codebookcodes and bases, in order. For every parent,
        yield a codebookcode, until the first non-time-limited parent is found.
        """
        for codebook in [self] + self.bases:
            for co in codebook.codebookcodes:
                if co.code_id == code.id: 
                    yield co
                    if not (co.validfrom or co.validto): return
    
    def get_hierarchy(self, date=None):
        """Return a mapping of code, parent pairs that forms the hierarchy of this codebook
        
        A code is in a codebook if (a) it is listed in its direct codebookcodes, or
        (b) if it is in any of the base codebooks and not explicitly hidden in this codebook.
        The parent of a code is its parent in the codebook it came from, ie in this codebook
        if listed, otherwise in the first base that listed it.
        
        If date is not given, the current date is used as default
        If validfrom and/or validto are given, only consider codebook codes
          where validfrom <= date < validto.
        """
        # go through hierarchy sources in reverse order and update result dict
        # so newest overrides oldest
        if date is None: date = datetime.now()
        result = {}
        for base in reversed(list(self.bases)):
            result.update(base.get_hierarchy(date))

        # Remove 'hide' objects from the result, and return
        for co in self.codebookcodes:
            if co.validfrom and date < co.validfrom: continue
            if co.validto and date >= co.validto: continue
            
            if co.hide:
                del result[co.code]
            else:
                result[co.code] = co.parent
        return result

    @property
    @cached
    def codes(self):
        """Returns a set of codes that are in this hierarchy
        All codes that would be in the hierarchy for a certain date are included
        (ie date restrictions are not taken into account)
        """
        codes = set(co.code for co in self.codebookcodes if not co.hide)
        for base in self.bases:
            codes |= base.codes
        codes -= set(co.code for co in self.codebookcodes if co.hide)
        return codes

    def get_code(self, code_id):
        """Return the code with the requested id. Raises a ValueError if not found"""
        # it might be useful to create a id : code mapping in get_hierarchy, but works for now
        for c in self.codes:
            if c.id == code_id: return c
        raise ValueError("Code with id {} not found in codebook {}".format(code_id, self.name))
    
    @invalidates
    def add_code(self, code, parent=None, **kargs):
        """Add the given code to the hierarchy, with optional given parent.
        Any extra arguments are passed to the CodebookCode constructor.
        Possible arguments include hide, validfrom, validto
        """
        if isinstance(parent, CodebookCode): parent = parent.code
        if isinstance(code, CodebookCode): code = code.code
        return CodebookCode.objects.create(codebook=self, code=code, parent=parent, **kargs)

    @invalidates
    def add_base(self, codebook, rank=None):
        """Add the given codebook as a base to this codebook"""
        if rank is None:
            maxrank = self.codebookbase_set.aggregate(models.Max('rank'))['rank__max']
            rank = maxrank+1 if maxrank is not None else 0
        return CodebookBase.objects.create(subcodebook=self, supercodebook=codebook, rank=rank)

    def cache_labels(self, language):
        """Ask the codebook to cache the labels on its objects in that language"""
        # HACK to cache cache labels per language
        if not hasattr(self, '_cache_labels_languages'):
            self._cache_labels_languages = set()
        elif language in self._cache_labels_languages:
            return
        self._cache_labels_languages.add(language)

        q = Label.objects.filter(language=language, code__in=self.codes)
        for l in q:
            self.get_code(l.code_id)._cache_label(language, l.label)

class CodebookBase(AmcatModel):
    """Many-to-many field (codebook : codebook) with ordering"""
    id = models.AutoField(primary_key=True, db_column='codebook_base_id')
    supercodebook = models.ForeignKey(Codebook, db_index=True, related_name="+")
    subcodebook = models.ForeignKey(Codebook, db_index=True)
    
    rank = models.IntegerField(default=0, null=False)
    
    class Meta():
        db_table = 'codebooks_bases'
        app_label = 'amcat'
        ordering = ['rank']
        unique_together = ("supercodebook", "subcodebook")

class Function(AmcatModel):
    """Specification of code book parent-child relations"""
    id = models.IntegerField(primary_key=True, db_column='function_id')
    label = models.CharField(max_length=100, null=False, unique=True)
    description = models.TextField(null=True)

    __label__ = 'label'
    class Meta():
        db_table = 'codebooks_functions'
        app_label = 'amcat'
        
            
class CodebookCode(AmcatModel):
    """Many-to-many field (codebook : code) with additional properties"""
    id = models.AutoField(primary_key=True, db_column='codebook_object_id')
    
    codebook = models.ForeignKey(Codebook, db_index=True)
    
    code = models.ForeignKey(Code, db_index=True, related_name="+")
    parent = models.ForeignKey(Code, db_index=True, related_name="+", null=True)
    hide = models.BooleanField(default=False)               

    validfrom = models.DateTimeField(null=True)
    validto = models.DateTimeField(null=True)
    function = models.ForeignKey(Function, default=0)

    def save(self, *args, **kargs):
        self.validate()
        super(CodebookCode, self).save(*args, **kargs)

    @cached
    def get_codebook(self):
        """Get the cached codebook belonging to this code"""
        return get_codebook(self.codebook_id)
        
    @cached
    def get_code(self):
        """Get the cached code object"""
        return self.get_codebook().get_code(self.code_id)
        
    def validate(self):
        """Validate whether this relation obeys validity constraints:
        1) a relation can't specify a parent and hide at the same time
        2) a relation cannot have a validfrom later than the validto
        3) a child can't occur twice unless the periods are non-overlapping
        """
        if self.parent and self.hide:
            raise ValueError("A codebook code can either hide or provide a parent, not both!")
        if self.validto and self.validfrom and self.validto < self.validfrom:
            raise ValueError("A codebook code validfrom ({}) is later than its validto ({})"
                             .format(self.validfrom, self.validto))
        # uniqueness constraints:
        for co in self.get_codebook().codebookcodes:
            
            if co == self: continue # 
            if co.code != self.code: continue
            if self.validfrom and co.validto and self.validfrom >= co.validto: continue
            if self.validto and co.validfrom and self.validto <= co.validfrom: continue
            raise ValueError("Codebook code {!r} overlaps with {!r}".format(self, co))
        
    def __unicode__(self):
        return "{0.code}:{0.parent} ({0.codebook}, {0.validfrom}-{0.validto})".format(self)
    
    class Meta():
        db_table = 'codebooks_codes'
        app_label = 'amcat'
        #unique_together = ("codebook", "code", "function_id", "validfrom")
        # TODO: does not really work since NULL!=NULL
    
###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################
        
from amcat.tools import amcattest

class TestCodebook(amcattest.PolicyTestCase):
    PYLINT_IGNORE_EXTRA = "W0212",

    
    def test_create(self):
        """Can we create objects?"""
        c = amcattest.create_test_codebook()

        o = amcattest.create_test_code()
        co = c.add_code(o)
        co2 = c.add_code(Code.objects.create(), parent=o)
        
        self.assertIn(co, c.codebookcodes)
        #self.assertIn(o, c.codes)
        self.assertEqual(co2.parent, o)


        
    def standardize(self, codebook, **kargs):
        """return a dense hierarchy serialiseation for easier comparisons"""
        
        return ";".join(sorted({"{0}:{1}".format(*cp) 
                                for cp in codebook.get_hierarchy(**kargs).items()}))

    def test_hierarchy(self):
        """Does the code/parent base class resolution work"""

        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]

        # A: a
        #    +b
        #     +c
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b, a)
        A.add_code(c, b)
        self.assertEqual(self.standardize(A), 'a:None;b:a;c:b')

        # D: d
        #    +e
        #    +f
        D = amcattest.create_test_codebook(name="D")
        D.add_code(d)
        D.add_code(e, d)
        D.add_code(f, d)
        self.assertEqual(self.standardize(D), 'd:None;e:d;f:d')
        
        # A+D: a
        #      +b
        #       +c
        #      d
        #      +e
        #      +f
        AD = amcattest.create_test_codebook(name="A+D")
        AD.add_base(A)
        AD.add_base(D)
        self.assertEqual(self.standardize(AD), 'a:None;b:a;c:b;d:None;e:d;f:d')
        # now let's hide c and redefine e to be under b
        AD.add_code(c, hide=True)
        AD.add_code(e, parent=b)
        self.assertEqual(self.standardize(AD), 'a:None;b:a;d:None;e:b;f:d')

        # Test precendence between bases
        # B: b
        #    +d
        #    +e
        B = amcattest.create_test_codebook(name="B")
        B.add_code(b)
        B.add_code(d, b)
        B.add_code(e, b)
        self.assertEqual(self.standardize(B), 'b:None;d:b;e:b')
        # D+B: d     B+D: b
        #      +e         +d
        #      +f          +f
        #      b          +e
        DB = amcattest.create_test_codebook(name="D+B")
        DB.add_base(D)
        DB.add_base(B)
        self.assertEqual(self.standardize(DB), 'b:None;d:None;e:d;f:d')
        BD = amcattest.create_test_codebook(name="B+D")
        BD.add_base(B)
        BD.add_base(D)
        self.assertEqual(self.standardize(BD), 'b:None;d:b;e:b;f:d')

    def test_get_codebook(self):
        """Test whether using get_codebook results in shared objects"""
        cid = amcattest.create_test_codebook().pk
        c1 = get_codebook(cid)
        c2 = get_codebook(cid)
        self.assertIs(c1, c2)
        c3 = amcattest.create_test_codebook()
        self.assertIsNot(c1, c3)
        c4 = get_codebook(c3.id)
        self.assertEqual(c3, c4)        
        self.assertIsNot(c1, c4)   
        self.assertNotEqual(c1, c4)
    
        
        
    def test_validation(self):
        """Test whether codebookcode validation works"""
        a, b, c, d = [amcattest.create_test_code(label=l) for l in "abcd"]
        A = amcattest.create_test_codebook(name="A")
        self.assertRaises(ValueError, A.add_code, a, b, hide=True)
        self.assertRaises(ValueError, A.add_code, a, validfrom=datetime(2010, 1, 1),
                          validto=datetime(1900, 1, 1))
        A.add_code(a)
        A.add_code(b)
        A.add_code(c, a)
        self.assertRaises(ValueError, A.add_code, c, a)
        self.assertRaises(ValueError, A.add_code, c, b)
        self.assertRaises(ValueError, A.add_code, c, hide=True)
        
        A.add_code(d, a, validto=datetime(2010, 1, 1))
        A.add_code(d, b, validfrom=datetime(2010, 1, 1))

        self.assertRaises(ValueError, A.add_code, d, a)
        self.assertRaises(ValueError, A.add_code, d, a, validto=datetime(1900, 1, 1))
        self.assertRaises(ValueError, A.add_code, d, a, validfrom=datetime(1900, 1, 1))

        # different code book should be ok
        B = amcattest.create_test_codebook(name="B")
        B.add_code(a)
        B.add_code(c, a)
        
        
    def test_get_timebound_functions(self):
        """Test whether time-bound functions are returned correctly"""
        a, b, c = [amcattest.create_test_code(label=l) for l in "abc"]
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(c, a, validfrom=datetime(2010, 1, 1))
        self.assertEqual(self.standardize(A), 'a:None;c:a')
        self.assertEqual(self.standardize(A, date=datetime(1900, 1, 1)), 'a:None')
        A.add_code(b)
        A.add_code(c, b, validto=datetime(2010, 1, 1))
        self.assertEqual(self.standardize(A, date=datetime(2009, 12, 31)), 'a:None;b:None;c:b')
        self.assertEqual(self.standardize(A, date=datetime(2010, 1, 1)), 'a:None;b:None;c:a')
        self.assertEqual(self.standardize(A, date=datetime(2010, 1, 2)), 'a:None;b:None;c:a')
        
     
    def test_codes(self):
        """Test the codes property"""
        a, b, c, d = [amcattest.create_test_code(label=l) for l in "abcd"]
        
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b, a)
        A.add_code(c, a, validfrom=datetime(1910, 1, 1), validto=datetime(1920, 1, 1))

        self.assertEqual(A.codes, set([a, b, c]))

        B = amcattest.create_test_codebook(name="B")
        B.add_code(d, b)
        self.assertEqual(B.codes, set([d]))

        B.add_base(A)
        self.assertEqual(B.codes, set([a, b, c, d]))
        
    def test_codebookcodes(self):
        """Test the get_codebookcodes function"""
        def _copairs(codebook, code):
            """Get (child, parent) pairs for codebookcodes"""
            for co in codebook.get_codebookcodes(code):
                yield co.code, co.parent
            
            
        
        a, b, c, d, e = [amcattest.create_test_code(label=l) for l in "abcde"]
        
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)
        A.add_code(c, a, validfrom=datetime(1910, 1, 1), validto=datetime(1920, 1, 1))
        A.add_code(c, b, validfrom=datetime(1920, 1, 1), validto=datetime(1930, 1, 1))
        A.add_code(d, a)
        A.add_code(e, a)

        self.assertEqual(set(_copairs(A, a)), {(a, None)})
        self.assertEqual(set(_copairs(A, c)), {(c, a), (c, b)})
        self.assertEqual(set(_copairs(A, d)), {(d, a)})
        self.assertEqual(set(_copairs(A, e)), {(e, a)})
        
        B = amcattest.create_test_codebook(name="B")
        B.add_code(d, b)
        B.add_code(e, b, validfrom=datetime(2012, 1, 1))
        B.add_base(A)
        self.assertEqual(set(_copairs(B, d)), {(d, b)})
        self.assertEqual(set(_copairs(B, e)), {(e, b), (e, a)})
        self.assertEqual(set(_copairs(B, c)), {(c, a), (c, b)})
        
        
        


        
if __name__ == '__main__':
    c = get_codebook(-5001)
    import time
    from amcat.tools.djangotoolkit import list_queries
    
    with list_queries(output=print, printtime=True):
        set(c.codes)
    with list_queries(output=print, printtime=True):
        set(c.codes)
    
