###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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
import collections
import logging
import itertools

from datetime import datetime
from collections import OrderedDict
from itertools import product, chain
from typing import Tuple, Iterable, Optional, Dict, List

from django.db import models
from django.db.models import Q

from amcat.tools.model import AmcatModel
from amcat.models.coding.code import Code, Label
from amcat.models import Language
from amcat.tools.djangotoolkit import distinct_args


log = logging.getLogger(__name__)


# Used in Codebook.get_tree()
class TreeItem(collections.namedtuple("TreeItem", ["code_id", "codebookcode_id", "children", "hidden", "label", "ordernr"])):
    def get_descendants(self):
        childrens_children = (c.get_descendants() for c in self.children)
        return self.children + tuple(itertools.chain.from_iterable(childrens_children))


def get_tree_levels(tree: Tuple[TreeItem]) -> Iterable[Tuple[TreeItem]]:
    """Get levels of a tree. That is, given a codebook:

        A
        - B
        -- C
        -- D
        - E
        - F
        -- G
        H

    return a tuple where the nth item of that tuple contains:

        0: A, H
        1: B, E, F
        2: C, D, G

    """
    if tree:
        yield tree

    childrens_levels = [get_tree_levels(child.children) for child in tree]

    while True:
        new_level = []

        for child_levels in childrens_levels:
            try:
                child_level = next(child_levels)
            except StopIteration:
                pass
            else:
                new_level.extend(child_level)

        if not new_level:
            break

        yield new_level


def get_max_tree_depth(tree: Tuple[TreeItem]) -> int:
    """Selects the node furthest from a root node, and counts the number of edges between it and the root. Note that
    this is undefined for empty trees, thus throwing an error when this function is called with an empty tree"""
    def _get_max_tree_depth(node, n):
        if node.children:
            return max(_get_max_tree_depth(c, n=n+1) for c in node.children)
        else:
            return n

    if not tree:
        raise ValueError("Depth for empty trees is undefined!")
    else:
        return max(_get_max_tree_depth(n, 0) for n in tree)


def get_max_tree_level(tree: Tuple[TreeItem]) -> int:
    """Counts the number of levels in this tree. Empty trees have zero levels."""
    try:
        return 1 + get_max_tree_depth(tree)
    except ValueError:
        return 0


def sort_codebookcodes(ccodes):
    ccodes.sort(key=lambda ccode: (ccode.ordernr, ccode.code_id))


def sort_tree(tree: Tuple[TreeItem]) -> Tuple[TreeItem]:
    tree = sorted(tree, key=lambda ti: (ti.ordernr, ti.code_id))
    for child in tree:
        child.children = sort_tree(child.children)
    return tuple(tree)


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
        self._labels = collections.defaultdict(dict)

    @property
    def cached(self):
        return self._codebookcodes is not None

    def cache(self, select_related=(), prefetch_related=(), only=None):
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
        if only is not None:
            # Allow efficient caching of codes
            only = tuple(only) + ("parent_id", "code_id")

        # create cache if needed, see query.py l. 1638
        if not hasattr(self, '_prefetched_objects_cache'):
            self._prefetched_objects_cache = {}

        # Fetch codebookcodes and put them in caches
        ccodes = CodebookCode.objects.filter(codebook=self)
        if only is not None:
            ccodes = ccodes.only(*only)

        ccodes = ccodes.select_related("code", *select_related)
        ccodes = ccodes.prefetch_related(*prefetch_related)
        self._prefetched_objects_cache['codebookcode_set'] = ccodes = tuple(ccodes)
        self._codes = OrderedDict((cc.code_id, cc.code) for cc in ccodes)
        self._codebookcodes = collections.defaultdict(list)

        for ccode in ccodes:
            # Cache the parent property
            if ccode.parent_id is not None:
                ccode._parent_cache = self._codes[ccode.parent_id]

            # Make sure all Code objects are the same
            ccode._code_cache = self._codes[ccode.code_id]
            self._codebookcodes[ccode.code_id].append(ccode)

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
            labels = Label.objects.filter(code__id__in=codes).distinct(*distinct_args("language"))
            languages = labels.values_list("language_id", flat=True)
            all_labels = True
        else:
            languages = [l.id if isinstance(l, Language) else int(l) for l in languages]
            all_labels = False

        labels = Label.objects.filter(language__id__in=languages, code__id__in=codes)
        labels = labels.values_list("code_id", "language_id", "label")

        if all_labels:
            for code_id, lan_id, label in labels:
                self._codes[code_id]._cache_label(lan_id, label)
                self._labels[code_id][lan_id] = label
            for code in self._codes.values():
                code._all_labels_cached = True
        else:
            codes = set(product(codes, languages))
            for code_id, lan_id, label in labels:
                self._codes[code_id]._cache_label(lan_id, label)
                self._labels[code_id][lan_id] = label
                codes.remove((code_id, lan_id))

            for code_id, lan_id in codes:
                # These codes don't have a label. We need to explicitly cache them to prevent
                # database trips.
                self._codes[code_id]._cache_label(lan_id, None)

        self._cached_labels |= self._cached_labels.union(set(languages))

    @property
    def codebookcodes(self):
        codes = self.codebookcode_set.all()
        if self.cached:
            # TODO: _result_cache should be lazy
            codes._result_cache = self._prefetched_objects_cache['codebookcode_set']

        return codes

    def get_codebookcodes(self, code):
        """Return a sequence of codebookcode objects for this code in the codebook"""
        if self.cached: return self._codebookcodes[code.id]
        return (co for co in self.codebookcodes if co.code_id == code.id)


    def get_codebookcode(self, code, date=None):
        """Get the (unique or first) codebookcode from *this* codebook corresponding
        to the given code with the given date, or None if not found"""
        if date is None: date = datetime.now()

        for co in self.get_codebookcodes(code):
            if co.validfrom and date < co.validfrom: continue
            if co.validto and date >= co.validto: continue
            return co

    def _get_hierarchy_ids(self, date=None, include_hidden=False):
        """Return id:id/None mappings for get_hierarchy."""
        if date is None: date = datetime.now()

        if not self.cached:
            valid_from = Q(validfrom=None) | Q(validfrom__lte=date)
            valid_to = Q(validto=None) | Q(validto__gt=date)
            codes = self.codebookcodes.filter(valid_from, valid_to)
            if not include_hidden: codes = codes.filter(hide=False)
            return OrderedDict(codes.values_list("code_id", "parent_id"))

        codes = (co for co in self.codebookcodes
                 if not ((co.validfrom and date < co.validfrom) or
                         (co.validto and date >= co.validto)))

        if include_hidden:
            return OrderedDict((co.code_id, co.parent_id) for co in codes)
        return OrderedDict((co.code_id, co.parent_id) for co in codes if not co.hide)


    def _get_node(self, children, node, seen):
        """
        Return a namedtuple as described in get_tree(). Raises a CodebookCycleException
        when it detects a cycle.
        """
        if node in seen:
            raise CodebookCycleException("Cycle? {}".format(node))

        cc = self.get_codebookcode(node)
        seen.add(node)

        return TreeItem(
            code_id=node.id, codebookcode_id=cc.id if cc else None,
            hidden=cc.hide if cc else None, ordernr=cc.ordernr if cc else None,
            children=self._walk(children, children[node], seen),
            label=node.label
        )

    def _walk(self, children, nodes, seen):
        return tuple(self._get_node(children, n, seen) for n in nodes)

    def get_tree(self, include_hidden=True, date=None, roots=None):
        """
        Get a tree representation of the tuples returned by get_hierarchy. For each root
        it yields a namedtuple("TreeItem", ["code_id", "children", "hidden"]) where
        parent points to a TreeItem, and children to a list of TreeItems.
        
        This method will check for cycli and raise an error when one is detected.

        @param include_hidden: include hidden codes
        @param roots: start tree at given nodes.
        @type roots: List of CodebookCodes
        @requires: roots in self.codebookcodes
        """
        children = collections.defaultdict(list)
        hierarchy = self.get_hierarchy(include_hidden=include_hidden, date=date)
        nodes = roots or self.get_roots(include_hidden=include_hidden, date=date)
        seen = set()

        for child, parent in hierarchy:
            if parent:
                children[parent].append(child)

        return self._walk(children, nodes, seen)

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

        if self.cached:
            codes = self._codes
        else:
            code_ids = set(hierarchy.keys()) | set(hierarchy.values()) - {None}
            codes = Code.objects.in_bulk(code_ids)

        return (
            (codes[cid] if cid in codes else None, codes[pid] if pid in codes else None)
            for cid, pid in hierarchy.items()
        )

    def _get_aggregation_mapping(self):
        for root in self.get_tree():
            for child in root.children:
                yield (child.label, root.label)

    def get_aggregation_mapping(self):
        """Returns a mapping from label to label, to allow substantive analysis in codingjob
        export options. That is, with the codebook:

            A
            - B
            - C
            D
            - F

        This function would result in a dictionary:

            {B.label: A.label, C.label: A.label, F.label: D.label}

        Only nodes which descend directly from the root nodes will be considerd.

        Note: make sure labels are cached with cache_labels; this method will perform very
        poorly without the cache ready.
        """
        if not self.cached: raise ValueError("Codebook not cached. Use .cache().")
        return dict(self._get_aggregation_mapping())

    def get_code_ids(self, include_hidden=False, include_parents=False):
        """Returns a set of code_ids that are in this hierarchy
        @param include_hidden: if True, include codes hidden by *this* codebook
        """
        code_ids = self.codebookcodes.values_list("code_id", flat=True)

        if not include_hidden:
            code_ids = code_ids.filter(hide=False)

        if self.cached and include_hidden:
            code_ids._result_cache = self._codes.keys()
        elif self.cached:
            code_ids._result_cache = [co.code_id for co in self.codebookcodes if not co.hide]

        return code_ids

    def get_codes(self, include_hidden=False):
        """Returns a set of codes that are in this hierarchy
        All codes that would be in the hierarchy for a certain date are included
        (ie date restrictions are not taken into account)
        @param include_hidden: if True, include codes hidden by *this* codebook
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
            return self.codebookcodes.select_related("code").get(code_id=code_id).code
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

    def add_codes(self, codes):
        """
        Add a list of codes (and their parents) to the codebook

        @param codes: a list/tuple of Code objects or a list/tuple of (code, parent) pairs (both Code objects, parent
        optionally None for roots). If parents are given, all parent Codes should exist in the codebook
        or be included as a code in the codes list.
        """
        if len(codes) == 0: return

        # Create pairs with all parents empty if this is a list of codes
        if isinstance(codes[0], Code):
            codes = [(c, None) for c in codes]

        ccodes = {code.id: CodebookCode(codebook=self, code=code) for code in
                  chain(*codes) if code and not self._code_in_codebook(code)}

        # Set parents for all codes
        for child, parent in codes:
            if self._code_in_codebook(child):
                raise ValueError("{} already in codebook".format(child))
            elif parent:
                ccodes[child.id].parent = parent

        CodebookCode.objects.bulk_create(ccodes.values())
        self.invalidate_cache()

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
                self._codebookcodes[parent.id].append(_parent)
                self._codes[parent.id] = parent

                # Keep ordering according to ordernr
                sort_codebookcodes(self._codebookcodes[parent.id])

        # Update child (`code`) caching
        if self.cached:
            self._codebookcodes[code.id].append(child)
            sort_codebookcodes(self._codebookcodes[code.id])
            code = child._code_cache = self._codes[code.id] = self._codes.get(code.id, code)
            if parent: child._parent_cache = self._codes[parent.id]

        # Update label cache for added codes
        if self.cached and update_label_cache and self._cached_labels:
            codes = [c for c in (parent, child.code) if c is not None]
            self.cache_labels(*self._cached_labels, codes=codes)

        return child

    def create_code(self, label, language, parent=None, **kargs):
        """
        Convenience method to create a new code with given language:label,
        and add it to this codebook under the optional parent
        """

        return self.add_code(Code.create(label, language), parent=parent, **kargs)

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

    def get_roots(self, **kwargs):
        """
        @return: the root nodes in this codebook
        @param kargs: passed to get_hierarchy (e.g. date, include_hidden)
        """
        parents, children, roots = set(), set(), set()
        hierarchy = tuple(self.get_hierarchy(**kwargs))

        for child, parent in hierarchy:
            if parent is None:
                roots.add(child)

            parents.add(parent)
            children.add(child)

        # Keep ordering by using order of hierarchy
        roots |= parents - children - {None, }
        hierarchy = OrderedDict(hierarchy)
        codes = chain(hierarchy.keys(), hierarchy.values())
        codes = {code: i for i, code in enumerate(codes)}
        return sorted(roots, key=codes.get)

    def get_children(self, code, **kargs):
        """
        @return: the children of code in this codebook
        @param kargs: passed to get_hierarchy (e.g. date, include_hidden)
        """
        return (c for (c, p) in self.get_hierarchy(**kargs) if p == code)

    def get_ancestor_ids(self, code_id):
        """
        Return a sequence of ancestor ids for this code, from the code itself up to a root of the codeobok
        @parem code: a Code object in this codebook
        """
        hierarchy = self._get_hierarchy_ids()

        def _get_parent(code):
            for child, parent in hierarchy.items():
                if child == code:
                    return parent
            raise ValueError("Code {code!r} not in hierarchy!")

        seen = set()
        while True:
            yield code_id
            seen.add(code_id)
            parent = hierarchy[code_id]  #_get_parent(code_id)
            if parent is None:
                return
            elif parent in seen:
                raise ValueError("Cycle in hierarchy: parent {parent} already in seen {seen}".format(**locals()))
            seen.add(parent)

            code_id = parent

    def get_language_ids(self):
        """
        For all labels for all codes in this codebook, return the language id.
        """
        # For some reason, postgres is *really* slow when querying with joins / distincts, so
        # we'll compile these queries by using set logic.
        codes = self.codes.values_list("id", flat=True)
        labels = Label.objects.filter(code__id__in=codes).order_by()
        return set(labels.values_list("language__id", flat=True))

    def recycle(self):
        """Move this job to the recycle bin"""
        from amcat.models.project import LITTER_PROJECT_ID

        self.project_id = LITTER_PROJECT_ID
        self.save()


class CodebookCode(AmcatModel):
    """Many-to-many field (codebook : code) with additional properties"""
    id = models.AutoField(primary_key=True, db_column='codebook_object_id')

    codebook = models.ForeignKey(Codebook, db_index=True)

    code = models.ForeignKey(Code, db_index=True, related_name="codebook_codes")
    parent = models.ForeignKey(Code, db_index=True, related_name="+", null=True)
    hide = models.BooleanField(default=False)

    validfrom = models.DateTimeField(null=True)
    validto = models.DateTimeField(null=True)

    ordernr = models.IntegerField(default=0, null=False, db_index=True, help_text=(
        "Annotator should order according codes according to this number."
    ))

    def save(self, *args, **kargs):
        if kargs.pop("validate", True):
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
            if co == self: continue  #
            if co.code_id != self.code_id: continue
            if self.validfrom and co.validto and self.validfrom >= co.validto: continue
            if self.validto and co.validfrom and self.validto <= co.validfrom: continue
            raise ValueError("Codebook code {!r} overlaps with {!r}".format(self, co))

    def __str__(self):
        return "{0.code}:{0.parent} ({0.codebook}, {0.validfrom}-{0.validto})".format(self)

    class Meta():
        db_table = 'codebooks_codes'
        app_label = 'amcat'
        ordering = ("ordernr",)
        #unique_together = ("codebook", "code", "validfrom")
        # TODO: does not really work since NULL!=NULL
