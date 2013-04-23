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
from amcat.models.coding.code import Code, Label
from django.core.exceptions import ValidationError



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


    def cache(self):
        """
        Recursively cache bases and objects in this codebook
        """
        # create cache if needed, see query.py l. 1638
        if not hasattr(self, '_prefetched_objects_cache'):
                self._prefetched_objects_cache = {}

        # Check if codebookbases is already cached
        if 'codebookbases' in self._prefetched_objects_cache:
            return

        self._prefetched_objects_cache['codebookbases'] = self.codebookbases.prefetch_related("base")
        for base in self.bases:
            base.cache()

        self._prefetched_objects_cache['codebookcodes'] = self.codebookcodes.prefetch_related("code", "parent")
        list(self.codebookcodes.all())
        
    @property
    def bases(self):
        """Return the base codebooks in the right order"""
        return [codebookbase.base for codebookbase in self.codebookbases.all()]

    @property
    def codebookcodes(self):
        """Return a list of codebookcodes with code and parent prefetched.
        This functions mainly to provide caching for the codebook codes"""
        return self.codebookcode_set.select_related("code", "parent")

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

    def get_codebookcode(self, code, date=None):
        """Get the (unique or first) codebookcode from *this* codebook corresponding
        to the given code with the given date, or None if not found"""
        if date is None: date = datetime.now()
        for co in self.codebookcodes:
            if co.code_id == code.id:
                if co.validfrom and date < co.validfrom: continue
                if co.validto and date >= co.validto: continue
                return co


    def _get_hierarchy_ids(self, date=None, include_hidden=False):
        """Return id:id/None mappings for get_hierarchy"""
        if date is None: date = datetime.now()
        result = {}
        for base in reversed(list(self.bases)):
            result.update(base._get_hierarchy_ids(date))

        for co in self.codebookcodes:
            if co.validfrom and date < co.validfrom: continue
            if co.validto and date >= co.validto: continue

            if co.hide and not include_hidden:
                del result[co.code_id]
            else:
                result[co.code_id] = co.parent_id
        return result

    def get_hierarchy(self, date=None, include_hidden=False):
        """Return a sequence of code, parent pairs that forms the hierarchy of this codebook

        A code is in a codebook if (a) it is listed in its direct codebookcodes, or
        (b) if it is in any of the base codebooks and not explicitly hidden in this codebook.
        The parent of a code is its parent in the codebook it came from, ie in this codebook
        if listed, otherwise in the first base that listed it.

        If date is not given, the current date is used as default
        If validfrom and/or validto are given, only consider codebook codes
          where validfrom <= date < validto.
        """
        hierarchy = self._get_hierarchy_ids(date, include_hidden)
        code_ids = set(hierarchy.keys()) | set(hierarchy.values()) - set([None])
        codes = dict((c.id, c) for c in Code.objects.filter(pk__in=code_ids))


        for codeid, parentid in hierarchy.iteritems():
            code = codes[codeid]
            parent = codes[parentid] if parentid is not None else None
            yield code, parent

    def get_code_ids(self, include_hidden=False, include_parents=False):
        """Returns a set of code_ids that are in this hierarchy
        @param include_hidden: if True, include codes hidden by *this* codebook
                               (e.g. not by its bases)
        """
        code_ids = set()
        for base in self.bases:
            code_ids |= base.get_code_ids(include_parents=include_parents)
        if include_hidden:
            code_ids |= set(co.code_id for co in self.codebookcodes)
        else:
            for co in self.codebookcodes:
                if co.hide:
                    code_ids.discard(co.code_id)
                else:
                    code_ids.add(co.code_id)
        if include_parents:
            code_ids |= set(co.parent_id for co in self.codebookcodes)
            code_ids -= set([None])
        return code_ids

    def get_codes(self, include_hidden=False):
        """Returns a set of codes that are in this hierarchy
        All codes that would be in the hierarchy for a certain date are included
        (ie date restrictions are not taken into account)
        @param include_hidden: if True, include codes hidden by *this* codebook
                               (e.g. not by its bases)
        """
        ids = self.get_code_ids(include_hidden=include_hidden)
        return Code.objects.filter(pk__in=ids)

    def get_code(self, code_id):
        """Return a Code object from this codebook. This is better than using
        Code.objects.get(.) as this code can have labels etc. cached"""
        for code in self.get_codes():
            if code.id == code_id:
                return code
        raise Code.DoesNotExist()
    
    @property
    def codes(self):
        """Property for the codes included and not hidden in this codebook and its parents"""
        return set(self.get_codes())

    def add_code(self, code, parent=None, **kargs):
        """Add the given code to the hierarchy, with optional given parent.
        Any extra arguments` are passed to the CodebookCode constructor.
        Possible arguments include hide, validfrom, validto
        """
        if isinstance(parent, CodebookCode): parent = parent.code
        if isinstance(code, CodebookCode): code = code.code
        return CodebookCode.objects.create(codebook=self, code=code, parent=parent, **kargs)

    def add_base(self, codebook, rank=None):
        """Add the given codebook as a base to this codebook"""
        if rank is None:
            maxrank = self.codebookbases.aggregate(models.Max('rank'))['rank__max']
            rank = maxrank+1 if maxrank is not None else 0
        return CodebookBase.objects.create(codebook=self, base=codebook, rank=rank)

    def cache_labels(self, language):
        """Ask the codebook to cache the labels on its objects in that language"""

        # which labels need to be cached?
        codes = dict((c.id,  c)
                     for c in  Code.objects.filter(pk__in=self.get_code_ids(include_hidden=True,
                                                                            include_parents=True))
                     if not c.label_is_cached(language))
        if not codes: return

        q = Label.objects.filter(language=language, code__in=codes)
        for l in q:
            codes.pop(l.code_id)._cache_label(language, l.label)
        for code in codes.values():
            code._cache_label(language, None)

    def get_roots(self, include_missing_parents=False, **kargs):
        """
        @return: the root nodes in this codebook
        @param include_missing_parents: if True, also include nodes used as parent but not
                                        listed explictly as root or child
        @param kargs: passed to get_hierarchy (e.g. date, include_hidden)
        """
        parents = set()
        children = set()
        for child, parent in self.get_hierarchy(**kargs):
            if parent is None: yield child
            parents.add(parent)
            children.add(child)
        if include_missing_parents:
            for node in parents - children - set([None]):
                yield node


    def get_children(self, code, **kargs):
        """
        @return: the children of code in this codebook
        @param kargs: passed to get_hierarchy (e.g. date, include_hidden)
        """
        return (c for (c, p) in self.get_hierarchy(**kargs) if p==code)

    def _check_not_a_base(self, base):
        """Raises a ValidationError iff base is an ancestor of this codebook"""
        for b in self.bases:
            if b == base: raise ValidationError('Circular codebook hierarchy: '
                                                'Codebook {self} has {base} as base!'
                                                .format(**locals()))
            b._check_not_a_base(base)


    def get_ancestor_ids(self, code_id):
        """
        Return a sequence of ancestor ids for this code, from the code itself up to a root of the codeobok
        @parem code: a Code object in this codebook
        """
        hierarchy = self._get_hierarchy_ids()
        def _get_parent(code):
            for child, parent in hierarchy.iteritems():
                if child == code:
                    return parent
            raise ValueError("Code {code!r} not in hierarchy!")

        seen = set()
        while True:
            yield code_id
            seen.add(code_id)
            parent = hierarchy[code_id]#_get_parent(code_id)
            if parent is None:
                return
            elif parent in seen:
                raise ValueError("Cycle in hierarchy: parent {parent} already in seen {seen}".format(**locals()))
            seen.add(parent)

            code_id = parent
            
class CodebookBase(AmcatModel):
    """Many-to-many field (codebook : codebook) with ordering"""
    id = models.AutoField(primary_key=True, db_column='codebook_base_id')
    codebook = models.ForeignKey(Codebook, db_index=True, related_name='codebookbases')
    base = models.ForeignKey(Codebook, db_index=True, related_name="+")

    rank = models.IntegerField(default=0, null=False)

    class Meta():
        db_table = 'codebooks_bases'
        app_label = 'amcat'
        ordering = ['rank']
        unique_together = ("codebook", "base")

    def save(self, *args, **kargs):
        """Check that there are no loops"""
        self.base._check_not_a_base(self.codebook)
        super(CodebookBase, self).save(*args, **kargs)

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

    code = models.ForeignKey(Code, db_index=True, related_name="codebook_codes")
    parent = models.ForeignKey(Code, db_index=True, related_name="+",
                               null=True)
    hide = models.BooleanField(default=False)

    validfrom = models.DateTimeField(null=True)
    validto = models.DateTimeField(null=True)
    function = models.ForeignKey(Function, default=0)

    def save(self, *args, **kargs):
        self.validate()
        super(CodebookCode, self).save(*args, **kargs)

    def validate(self):
        """Validate whether this relation obeys validity constraints:
        1) a relation cannot have a validfrom later than the validto
        2) a child can't occur twice unless the periods are non-overlapping
        3) a parent-child relationship may not be hidden
        """
        if self.validto and self.validfrom and self.validto < self.validfrom:
            raise ValueError("A codebook code validfrom ({}) is later than its validto ({})"
                             .format(self.validfrom, self.validto))
        # uniqueness constraints:
        for co in self.codebook.codebookcodes:

            if co == self: continue #
            if co.code != self.code: continue
            if self.validfrom and co.validto and self.validfrom >= co.validto: continue
            if self.validto and co.validfrom and self.validto <= co.validfrom: continue
            raise ValueError("Codebook code {!r} overlaps with {!r}".format(self, co))

        if (self.parent != None) and self.hide:
            raise ValueError("Parent code {!r} of code {!r} hidden.".format(self.parent, self.code))

        
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

        return ";".join(sorted(set("{0}:{1}".format(*cp)
                                   for cp in codebook.get_hierarchy(**kargs))))

    def test_circular(self):
        """Are circular bases prevented from saving?"""
        A, B, C, D, E = [amcattest.create_test_codebook() for _x in range(5)]
        A.add_base(B)
        self.assertRaises(ValidationError, B.add_base, A)
        A.add_base(C)
        A.add_base(D)
        A.add_base(E)
        D.add_base(B)
        self.assertRaises(ValidationError, B.add_base, A)

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

        self.assertEqual(A.codes, {a, b, c})

        B = amcattest.create_test_codebook(name="B")
        B.add_code(d, b)
        self.assertEqual(B.codes, {d})

        B.add_base(A)
        #with self.checkMaxQueries(2, "Getting codes from base"):
        self.assertEqual(B.codes, {a, b, c, d})

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

        self.assertEqual(set(_copairs(A, a)), set([(a, None)]))
        self.assertEqual(set(_copairs(A, c)), set([(c, a), (c, b)]))
        self.assertEqual(set(_copairs(A, d)), set([(d, a)]))
        self.assertEqual(set(_copairs(A, e)), set([(e, a)]))

        B = amcattest.create_test_codebook(name="B")
        B.add_code(d, b)
        B.add_code(e, b, validfrom=datetime(2012, 1, 1))
        B.add_base(A)
        self.assertEqual(set(_copairs(B, d)), set([(d, b)]))
        self.assertEqual(set(_copairs(B, e)), set([(e, b), (e, a)]))
        self.assertEqual(set(_copairs(B, c)), set([(c, a), (c, b)]))


    def test_roots_children(self):
        """Does getting the roots and children work?"""
        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]

        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)
        A.add_code(e, a)
        A.add_code(d, c)
        A.add_code(f, a)

        self.assertEqual(set(A.get_roots()), set([a, b]))
        self.assertEqual(set(A.get_roots(include_missing_parents=True)), set([a, b, c]))

        self.assertEqual(set(A.get_children(a)), set([e, f]))
        self.assertEqual(set(A.get_children(c)), set([d]))
        self.assertEqual(set(A.get_children(d)), set())

    def test_get_ancestors(self):
        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a)
        A.add_code(b)
        A.add_code(c, b)
        A.add_code(e, a)
        A.add_code(d, c)
        A.add_code(f, a)
        self.assertEqual(list(A.get_ancestor_ids(f.id)), [f.id, a.id])
        self.assertEqual(list(A.get_ancestor_ids(a.id)), [a.id])
        B = amcattest.create_test_codebook(name="B")
        B.add_code(f, b)
        B.add_base(A)
        self.assertEqual(list(B.get_ancestor_ids(f.id)), [f.id, b.id])
        
    def todo_test_cache_labels(self):
        """Does caching labels work?"""
        from amcat.models.language import Language
        lang = Language.objects.get(pk=1)
        codes = set(amcattest.create_test_code(label=l, language=lang) for l in "abcdef")
        morecodes = set(amcattest.create_test_code(label=l, language=lang) for l in "abcdef")

        h = amcattest.create_test_code(label="hidden", language=lang)

        B = amcattest.create_test_codebook(name="B")
        map(B.add_code, morecodes)
        A = amcattest.create_test_codebook(name="A")
        map(A.add_code, codes)
        A.add_code(h, hide=True)
        C = amcattest.create_test_codebook(name="C")
        A.add_base(C)
        C.add_base(B)
        n_bases = 3

        maxq = n_bases * 2 + 1 # base + codebookcodes per base, codes
        with self.checkMaxQueries(maxq, "Cache Codes"):
            self.assertEqual(set(A.get_codes(include_hidden=True)),
                             codes | set([h]) | morecodes)

        with self.checkMaxQueries(1, "Cache labels"): # labels
            A.cache_labels(lang)

        with self.checkMaxQueries(0, "Cache labels again"):
            A.cache_labels(lang)

        A._cache_labels_languages = set()
        with self.checkMaxQueries(2, "Cache labels directly"): # codes, labels
            A.cache_labels(lang)

        with self.checkMaxQueries(0, "Print labels"):
            for c in codes:
                c.get_label(lang)
                str(c)
                unicode(c)
                repr(c)

        with self.checkMaxQueries(0, "Print labels via hierarchy"):
            for c, _p in A.get_hierarchy(include_hidden=True):
                c.get_label(lang)
                str(c)
                unicode(c)


    def todo_test_cache_labels_language(self):
        """Does caching labels for multiple language work
        esp. caching non-existence of a label"""
        from amcat.models.language import Language
        l1 = Language.objects.get(pk=1)
        a = amcattest.create_test_code(label="a", language=l1)
        l2 = Language.objects.get(pk=2)
        b = amcattest.create_test_code(label="b", language=l2)
        A = amcattest.create_test_codebook(name="A")
        A.add_code(a); A.add_code(b)

        with self.checkMaxQueries(4, "Cache labels"):
            A.cache_labels(l1)
            A.cache_labels(l2)

        a, b = map(get_code, [a.id, b.id])

        with self.checkMaxQueries(0, "Get exisitng labels"):
            self.assertEqual(a.get_label(l1), "a")
            self.assertEqual(b.get_label(l2), "b")

        with self.checkMaxQueries(0, "Get non-existing labels"):
            self.assertEqual(a.get_label(l2, l1), "a")
            self.assertEqual(b.get_label(l1, l2), "b")



    def todo_test_cache(self):
        """Can we cache getting bases and codes?"""
        codes = [amcattest.create_test_code(label=l) for l in "abcdef"]
        hiddencodes = [amcattest.create_test_code(label=l) for l in "ghijkl"]

        C = amcattest.create_test_codebook(name="C")
        B = amcattest.create_test_codebook(name="B")
        map(B.add_code, codes)
        B.add_code(hiddencodes[0])
        A = amcattest.create_test_codebook(name="A")
        [A.add_code(c, hide=True) for c in hiddencodes]
        A.add_base(B)
        B.add_base(C)

        A = Codebook.objects.get(pk=A.id)
        with self.checkMaxQueries(8, "cache codebook", output="print"):
            A.cache()

        with self.checkMaxQueries(0, "cache already cached codebook"):
            A.cache()
            
        with self.checkMaxQueries(0, "Bases for codebooks"):
            self.assertEqual(set(A.bases), {B})
            
        with self.checkMaxQueries(0, "Recursive bases for codebooks"):
            self.assertEqual(set(list(A.bases)[0].bases), {C})


        with self.checkMaxQueries(0, "Get direct codes"):
            self.assertEqual(set(co.code for co in A.codebookcodes), set(hiddencodes))
            
        return
        with self.checkMaxQueries(0, "Get Codes"):
            self.assertEqual(set(A.get_codes()), set(c.id for c in codes))

        return
    

        #clear_cache(Code)
        with self.checkMaxQueries(2, "Hidden Codes"):
            self.assertEqual(set(A.get_codes(include_hidden=True)), set(codes) | set(hiddencodes))

        with self.checkMaxQueries(0, "Cached codes per codebook"):
            self.assertEqual(set(A.get_codes(include_hidden=True)), set(codes) | set(hiddencodes))



if __name__ == '__main__':
    cb = get_codebook(-5001)
    from amcat.tools.djangotoolkit import list_queries

    with list_queries(output=print, printtime=True):
        set(cb.codes)
    with list_queries(output=print, printtime=True):
        set(cb.codes)
