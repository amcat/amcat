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
from django.db.models import Q

from amcat.tools.model import AmcatModel
from amcat.models.coding.code import Code, Label
from amcat.models import Language
from django.core.exceptions import ValidationError
from amcat.tools import toolkit

import collections

from itertools import product, chain, takewhile

# Used in Codebook.get_tree()
TreeItem = collections.namedtuple("TreeItem", ["code_id", "children", "hidden", "label"])

class CodebookCycleException(ValueError):
    pass

class Codebook(AmcatModel):
    """Model class for table codebooks

    Codebook caches values, so please use the provided methods to add or remove
    objects and bases or call the reset() method after changing them manually.
    """
    __label__ = 'name'

    id = models.AutoField(primary_key=True, db_column='codebook_id')
    project = models.ForeignKey("amcat.Project")
    name = models.TextField()

    def __init__(self, *args, **kwargs):
        super(Codebook, self).__init__(*args, **kwargs)
        self.invalidate_cache()

    class Meta():
        ordering = ['name']
        db_table = 'codebooks'
        app_label = 'amcat'

    def invalidate_cache(self):
        self._codebookcodes = None
        self._codes = None
        self._cached_labels = set()
        self._prefetched_objects_cache = {}

    @property
    def cached(self):
        return self._codebookcodes is not None

    def cache(self,select_related=(), prefetch_related=(), only=None):
        """
        Cache this codebook and its codes, with various options. Iterating over
        self.codebookcode_set.all() won't hit the database. After executing this
        method the following properties are available on this codebook:

            - _codes, which contains all codes for *this* codebook in a
            mapping id --> code
            - _codebookcodes, which contains all codebookcodes for *this*
            codebook in a mapping id --> codebookcodes, with codes begin
            an (empty) set of all codebookcodes.   

        For all pairs of Code-objects (x, y) retrieved by on of the methods above,
        the following holds: (x.id == y.id) <=> (x is y). And for Codebookcode:
        (x.code.id == y.code.id) <=> (x.code is y.code).

        @type select_related: tuple, list
        @param select_related: arguments for select_related on self.codebookcodes

        @type prefetch_related: tuple, list
        @param prefetch_related: arguments for prefetch_related on self.codebookcodes

        @type only: tuple, list
        @param only: arguments to pass to only on self.codebookcodes
        """
        if self.codebookbases.exists():
            raise NotImplementedError("Hierarchies with bases not yet supported.")

        if only is not None:
            # Allow efficient caching of codes
            only = tuple(only) + ("parent_id", "code_id")

        # create cache if needed, see query.py l. 1638
        if not hasattr(self, '_prefetched_objects_cache'):
            self._prefetched_objects_cache = {}

        # Fetch codebookcodes and put them in caches
        codes = CodebookCode.objects.filter(codebook=self)
        if only is not None:
            codes = codes.only(*only)

        codes = codes.select_related("code", *select_related)
        codes = codes.prefetch_related(*prefetch_related)
        self._prefetched_objects_cache['codebookcode_set'] = codes = tuple(codes)
        self._codes = { cc.code_id : cc.code for cc in codes }
        self._codebookcodes = collections.defaultdict(set)

        for ccode in codes:
            # Cache the parent property
            if ccode.parent_id is not None:
                ccode._parent_cache = self._codes[ccode.parent_id]

            # Make sure all Code objects are the same
            ccode._code_cache = self._codes[ccode.code_id]
            self._codebookcodes[ccode.code_id].add(ccode)

    def cache_labels(self, *languages, **kwargs):
        """
        Cache labels for the given languages. Will call cache() if not done yet. 

        @param languages: languages to cache. If no given, we will cache all languages.
        @param codes: only cache labels for given codes.
        """
        if not self.cached: self.cache()

        codes = kwargs.get("codes")
        if codes is None:
            # Cache all codes
            codes = self._codes.keys()
        else:
            codes = [(c.id if isinstance(c, Code) else int(c)) for c in codes]

        if not languages:
            # Cache ALL languages in this codebook
            labels = Label.objects.filter(code__id__in=codes).distinct("language") 
            languages = labels.values_list("language_id", flat=True)
        else:
            languages = [l.id if isinstance(l, Language) else int(l) for l in languages]

        codes = set(product(codes, languages))
        labels = Label.objects.filter(language__id__in=languages, code__id__in=codes)
        
        for code_id, lan_id, label in labels.values_list("code_id", "language_id", "label"):
            self._codes[code_id]._cache_label(lan_id, label)
            codes.remove((code_id, lan_id))

        for code_id, lan_id in codes:
            # These codes don't have a label. We need to explicitely cache them to prevent
            # database trips.
            self._codes[code_id]._cache_label(lan_id, None)

        self._cached_labels |= self._cached_labels.union(set(languages))

    @property
    def codebookcodes(self):
        return self.codebookcode_set.all()

    @property
    def bases(self):
        """Return the base codebooks in the right order"""
        return [codebookbase.base for codebookbase in self.codebookbases.all()]

    def get_codebookcodes(self, code):
        """Return a sequence of codebookcode objects for this code in the codebook

        Iterate over own codebookcodes and bases, in order. For every parent,
        yield a codebookcode, until the first non-time-limited parent is found.
        """
        if self.codebookbases.exists():
            raise NotImplementedError("Getting codebookcodes with bases not yet supported.")

        if self.cached:
            for co in self._codebookcodes[code.id]:
                yield co
            
        log.warn("get_codebookcodes() called without cache(). May be slow for multiple calls.")
        for co in self.codebookcodes:
            if co.code_id == code.id:
                yield co


    def get_codebookcode(self, code, date=None):
        """Get the (unique or first) codebookcode from *this* codebook corresponding
        to the given code with the given date, or None if not found"""
        if date is None: date = datetime.now()
    
        if self.cached:
            for co in self._codebookcodes[code.id]:
                if co.validfrom and date < co.validfrom: continue
                if co.validto and date >= co.validto: continue
                return co

            return

        log.warn("get_codebookcode() called without cache(). May be slow for multiple calls.")
        for co in self.codebookcodes:
            if co.code_id == code.id:
                if co.validfrom and date < co.validfrom: continue
                if co.validto and date >= co.validto: continue
                return co
    
    def _get_hierarchy_ids(self, date=None, include_hidden=False):
        """Return id:id/None mappings for get_hierarchy."""
        if date is None: date = datetime.now()

        if self.codebookbases.exists():
            raise NotImplementedError("Hierarchies with bases not yet supported.")

        if not self.cached:
            valid_from = Q(validfrom=None) | Q(validfrom__lte=date)
            valid_to = Q(validto=None) | Q(validto__gt=date)
            codes = self.codebookcodes.filter(valid_from, valid_to)
            if not include_hidden: codes = codes.filter(hide=False)
            return dict(codes.values_list("code_id", "parent_id"))
            
        codes = (co for co in self.codebookcodes.all()
                    if not ((co.validfrom and date < co.validfrom) or
                            (co.validto and date >= co.validto)))

        if include_hidden:
            return { co.code_id : co.parent_id for co in codes if not co.hide }

        return { co.code_id : co.parent_id for co in codes }

    def _get_node(self, include_labels, children, node, seen, labels=None):
        """
        Return a namedtuple as described in get_tree(). Raises a CodebookCycleException
        when it detects a cycle.
        """
        if node in seen:
            raise CodebookCycleException("Cycle? {}".format(node))

        cc = self.get_codebookcode(node)
        seen.add(node)

        return TreeItem(
            code_id=node.id, hidden=cc.hide if cc else None,
            children=self._walk(include_labels, children, children[node], seen),
            label=node.get_label(*(labels or self._cached_labels), fallback=labels is None) if include_labels else None
        )
        
    def _walk(self, include_labels, children, nodes, seen, labels=None):
        return tuple(self._get_node(include_labels, children, n, seen, labels=labels) for n in nodes)

    def get_tree(self, include_missing_parents=True, include_hidden=True, include_labels=True, get_labels=None, date=None):
        """
        Get a tree representation of the tuples returned by get_hierarchy. For each root
        it yields a namedtuple("TreeItem", ["code_id", "children", "hidden"]) where
        parent points to a TreeItem, and children to a list of TreeItems.
        
        This method will check for cycli and raise an error when one is detected.

        @param include_missing_parents: if True, also include nodes used as parent but not
                                            explicitly listed as root or child.
        @param include_hidden: include hidden codes
        @param include_labels: include .label property on each TreeItem
        @param get_labels: fetch labels in this order. This will not use fallback,
                            see docs Code.get_label().
        """
        children = collections.defaultdict(set)
        hierarchy = self.get_hierarchy(include_hidden=include_hidden, date=date)
        nodes = self.get_roots(include_missing_parents=include_missing_parents, include_hidden=include_hidden, date=date)
        seen = set()

        for child, parent in hierarchy:
            if parent:
                children[parent].add(child)

        tree = self._walk(include_labels, children, nodes, seen, get_labels)
        if len(seen) < CodebookCode.objects.filter(codebook=self).count():
            # Not all codes included in this tree.. cycle!
            raise CodebookCycleException("Graph disconnected")

        return tree

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
        if self.codebookbases.exists():
            raise NotImplementedError("Hierarchies with bases not yet supported.")

        hierarchy = self._get_hierarchy_ids(date, include_hidden)

        if self.cached:
            codes = self._codes
        else:
            code_ids = set(hierarchy.keys()) | set(hierarchy.values()) - set([None])
            codes = Code.objects.in_bulk(code_ids)

        codes[None] = None
        for code_id, parent_id in hierarchy.iteritems():
            yield (codes[code_id], codes[parent_id])

        if self._codes is not None:
            del codes[None]

    def get_code_ids(self, include_hidden=False, include_parents=False):
        """Returns a set of code_ids that are in this hierarchy
        @param include_hidden: if True, include codes hidden by *this* codebook
                               (e.g. not by its bases)
        """
        code_ids = set()

        for base in self.bases:
            code_ids |= base.get_code_ids(include_parents=include_parents)

        if include_hidden:
            if self.cached:
                code_ids |= set(self._codes.keys())
            else:
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
        codes = Code.objects.filter(pk__in=ids)

        if self.cached:
            codes._result_cache = [self._codes[aid] for aid in ids] 

        return codes

    def get_code(self, code_id):
        """Get code with id `code_id`. Uses cache if possible."""
        if self.cached:
            if code_id in self._codes:
                return self._codes[code_id]
            raise Code.DoesNotExist()

        try:
            return self.codebookcodes.get(code_id=code_id).code
        except CodebookCode.DoesNotExist:
            raise Code.DoesNotExist()
    
    @property
    def codes(self):
        """Property for the codes included and not hidden in this codebook and its parents"""
        return self.get_codes()

    def _code_in_codebook(self, code):
        """Returns whether a CodebookCode exists with code=code"""
        if self.cached: return code.id in self._codes
        return CodebookCode.objects.filter(codebook=self, code=code).exists()

    def add_code(self, code, parent=None, update_label_cache=True, **kargs):
        """Add the given code to the hierarchy, with optional given parent.
        Any extra arguments` are passed to the CodebookCode constructor.
        Possible arguments include hide, validfrom, validto.

        @type update_cache: boolean
        @param update_label_cache: if this codebook is cached, update its cache with the
            codes just given. cache_labels() will be called with languages = currently
            cached languages.
        """
        if isinstance(parent, CodebookCode): parent = parent.code
        if isinstance(code, CodebookCode): code = code.code

        child = CodebookCode.objects.create(codebook=self, code=code, parent=parent, **kargs)
    
        # Parent should also be in this codebook, else caching will fail
        if parent and not self._code_in_codebook(parent):
            _parent = CodebookCode.objects.create(codebook=self, code=parent)
            if self.cached:
                self._codebookcodes[parent.id].add(_parent)
                self._codes[parent.id] = parent
                
        # Update child (`code`) caching
        if self.cached:
            self._codebookcodes[code.id].add(child)
            child._code_cache = self._codes[code.id] = self._codes.get(code.id, code)
            if parent: child._parent_cache = self._codes[parent.id]

        # Update label cache for added codes
        if self.cached and update_label_cache and self._cached_labels:
            codes = [c for c in (parent, child) if c is not None]
            self.cache_labels(*self._cached_labels, codes=codes)

        return child

    def delete_codebookcode(self, codebookcode):
        """Delete this CodebookCode from this Codebook."""
        if self.cached:
            self._codebookcodes[codebookcode.code_id].remove(codebookcode)
            if not self._codebookcodes[codebookcode.code_id]:
                # No Codebookcodes left to refer to this code
                del self._codebookcodes[codebookcode.code_id]
                del self._codes[codebookcode.code_id]
                self.codebookcodes.filter(parent=codebookcode.code_id).update(parent=None)
        else:
            if not self.codebookcodes.filter(code=codebookcode.code_id).exists():
                self.codebookcodes.filter(parent=codebookcode.code_id).update(parent=None)

        codebookcode.delete()

    def delete_code(self, code):
        """Delete this code from this codebook. """
        map(self.delete_codebookcode, self.codebookcodes.filter(code=code))

    def add_base(self, codebook, rank=None):
        """Add the given codebook as a base to this codebook"""
        self.invalidate_cache()
        if rank is None:
            maxrank = self.codebookbases.aggregate(models.Max('rank'))['rank__max']
            rank = maxrank+1 if maxrank is not None else 0
        return CodebookBase.objects.create(codebook=self, base=codebook, rank=rank)


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
    parent = models.ForeignKey(Code, db_index=True, related_name="+", null=True)
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
        import datetime

        a, b, c, d, e, f = [amcattest.create_test_code(label=l) for l in "abcdef"]


        # A: b (validto = 2010)
        #    +a
        #
        # a should have parent b, even when requesting hierarchy of 2013.
        Z = amcattest.create_test_codebook(name="Z")
        Z.add_code(code=b, validto=datetime.datetime(2010, 1, 1))
        Z.add_code(code=a, parent=b)
        tree = Z.get_tree(datetime.datetime(2013,1,1))
        self.assertEqual(tree[0].children[0].label, 'a')

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
        # This feature is not yet implemented..
        """AD = amcattest.create_test_codebook(name="A+D")
        AD.add_base(A)
        AD.add_base(D)
        self.assertRaises(NotImplementedError, lambda: list(AD.get_hierarchy()))
        
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
        self.assertEqual(self.standardize(BD), 'b:None;d:b;e:b;f:d')"""


    def test_validation(self):
        """Test whether codebookcode validation works"""
        a, b, c, d = [amcattest.create_test_code(label=l) for l in "abcd"]
        A = amcattest.create_test_codebook(name="A")
        self.assertTrue(A.add_code(a,b,hide=True) != None)

        # Delete code added in previous statement
        A.delete_codebookcode(CodebookCode.objects.get(codebook=A, code=a, parent=b))
        A.delete_codebookcode(CodebookCode.objects.get(codebook=A, code=b))
        
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

        self.assertEqual(set(A.codes), {a, b, c})

        B = amcattest.create_test_codebook(name="B")
        
        B.add_code(d, b)
        self.assertEqual(set(B.codes), {d, b})

        # Bases not yet implemented
        #B.add_base(A)
        #with self.checkMaxQueries(2, "Getting codes from base"):
        #self.assertEqual(set(B.codes), {a, b, c, d})

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
        """B.add_base(A)
        self.assertEqual(set(_copairs(B, d)), set([(d, b)]))
        self.assertEqual(set(_copairs(B, e)), set([(e, b), (e, a)]))
        self.assertEqual(set(_copairs(B, c)), set([(c, a), (c, b)]))"""


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

        # Bases not yet implemented!
        """
        B.add_base(A)
        self.assertEqual(list(B.get_ancestor_ids(f.id)), [f.id, b.id])
        """

    def test_caching_correctness(self):
        """
        Each method gets decorated with {cache, cache_labels, cache+cache_labels} after which
        each of the tests above is re-run.
        """
        cached_functions = set([
            "get_codebookcodes", "get_codebookcode", "_get_hierarchy_ids", "get_tree",
            "get_hierarchy", "get_code_ids", "get_codes", "get_code", "add_code",
            "add_base", "get_roots", "get_children", "get_ancestor_ids"
        ])

        def _getattr(orig):
            def wrapped(self, name):
                if name in cached_functions:
                    self.cache()
                return orig(self, name)
            return wrapped
            
        ga = Codebook.__getattribute__
        Codebook.__getattribute__ = _getattr(ga) 

        try:
            self.test_create()
            self.test_hierarchy()
            self.test_validation()
            self.test_get_timebound_functions()
            self.test_codes()
            self.test_codebookcodes()
            self.test_roots_children()
            self.test_get_ancestors()
        finally:
            Codebook.__getattribute__ = ga 
            
        
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
