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
Utility module for keyword searches. This module is full of misnomers, maybe
move it to 'queryparser'?
"""

import logging
import re
from itertools import chain

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from amcat.models import Label, ArticleSet, CodingJob, Code
from amcat.tools.aggregate_es import aggregate, TermCategory
from amcat.tools.amcates import ES
from amcat.tools.caching import cached
from amcat.tools.toolkit import strip_accents
from amcat.tools import queryparser

REFERENCE_RE = re.compile(r"<(?P<reference>.*?)(?P<recursive>\+?)>")

log = logging.getLogger(__name__)

FIELD_MAP = {
    "term": "terms",
    "set": "sets"
}

def to_sortable_tuple(key):
    if isinstance(key, tuple):
        return tuple(map(to_sortable_tuple, key))
    elif isinstance(key, (ArticleSet, CodingJob)):
        return key.name.lower()
    elif isinstance(key, (Code, SearchQuery)):
        return key.label.lower()
    return key


class SelectionData:
    def __init__(self, data):
        self.__dict__.update(data)


def group_by_first_value(aggr):
    current_group = None
    nested_aggr = []

    for row in aggr:
        if not nested_aggr:
            current_group = row[0]

        if row[0] == current_group:
            nested_aggr.append(row[1:])
        else:
            yield current_group, nested_aggr
            nested_aggr = []

    if nested_aggr:
        yield current_group, nested_aggr

def to_nested(aggr):
    for row in aggr:
        if len(row) == 2:
            return aggr
    return ((group, to_nested(a)) for group, a in group_by_first_value(aggr))


class SelectionSearch:
    def __init__(self, form):
        """
        Form *must* be valid before passing.
        @type form: SelectionForm
        """
        self.es = ES()
        self.form = form
        self.data = SelectionData(form.cleaned_data)

    def _get_filters(self):
        """
        Get filters for dates,  articlesets and articles for given form. Yields
        iterables of tuples containing (filter_name, filter_value).

        @type form: SelectionForm
        """
        yield get_date_filters(
            self.data.start_date, self.data.end_date,
            self.data.on_date, self.data.datetype
        )

        yield (("sets", [a.id for a in self.data.articlesets]),)
        yield (("ids", self.data.article_ids or None),)

    @cached
    def get_filters(self):
        """Returns dict with filter -> value, which can be passed to elastic"""
        # Remove all filters which value is None
        return {k: v for k, v in chain(*self._get_filters()) if v is not None}

    @cached
    def get_query(self):
        """
        @rtype: str
        """
        return ' OR '.join('(%s)' % q.query for q in self.get_queries()) or None

    @cached
    def get_queries(self):
        """Get SearchQuery objects

        @rtype: iterable of SearchQuery"""
        if not self.data.query:
            return []
        codebook = self.data.codebook
        label_lan = self.data.codebook_label_language
        replacement_lan = self.data.codebook_replacement_language

        if codebook:
            codebook.cache_labels()

        queries = map(str.strip, self.data.query.split("\n"))
        #filter empty lines
        queries = filter(lambda x: x, queries)
        queries = map(SearchQuery.from_string, queries)

        resolved = resolve_queries(
            list(queries), codebook=codebook,
            label_language=label_lan,
            replacement_language=replacement_lan
        )

        return [q for q in resolved if not q.label.startswith("_")]

    @cached
    def get_count(self):
        try:
            return self.es.count(self.get_query(), self.get_filters())
        except queryparser.QueryParseError:
            # try queries one by one
            for i, q in enumerate(self.get_queries()):
                queryparser.parse_to_terms(q.query, context=(q.declared_label or i+1))
            # if error wasn't raised yet, re-raise original
            raise

    @cached
    def get_statistics(self):
        return self.es.statistics(self.get_query(), self.get_filters())

    def get_aggregate(self, categories, flat=True, objects=True):
        # If we're aggregating on terms, we don't want a global filter
        query = None
        if not any(isinstance(c, TermCategory) for c in categories):
            query = self.get_query()

        aggr = aggregate(query, self.get_filters(), categories, flat=flat, objects=objects)
        return sorted(aggr, key=to_sortable_tuple)

    def get_nested_aggregate(self, categories):
        return to_nested(self.get_aggregate(categories))

    def get_article_ids(self):
        return ES().query_ids(self.get_query(), self.get_filters())

    def _get_article_ids_per_query(self):
        for q in self.get_queries():
            yield q, list(ES().query_ids(q.query, self.get_filters()))

    def get_article_ids_per_query(self):
        return dict(self._get_article_ids_per_query())

    def get_articles(self, size=None, offset=0, fields=()):
        return ES().query(self.get_query(), self.get_filters(), True, size=size, from_=offset, _source=fields)


class SearchQuery(object):
    """
    Represents a query object that contains both a query and
    an optional label
    """

    def __init__(self, query, label=None):
        self.query = strip_accents(query)
        self.declared_label = _clean(label)
        self.label = self.declared_label or _clean(self.query)

    @classmethod
    def _get_label_delimiter(cls, query_string, label_delimiters):
        for d in label_delimiters:
            if d in query_string:
                return d

    @classmethod
    def from_string(cls, query_string, label_delimiters="#\t|"):
        """
        Returns a SearchQuery object, parsed from string `q`
        @raises: ValidationError if `q` is not valid query
        """
        query = query_string.strip()
        label_delimiter = cls._get_label_delimiter(query_string, label_delimiters)

        if not label_delimiter:
            return SearchQuery(query)

        label_delimiter = label_delimiter[0]
        pattern = label_delimiter.replace("|", "\\|") + "+"
        lbl, q = re.split(pattern, query, 1)

        if len(lbl) == 0:
            raise QueryValidationError("Delimiter ({label_delimiter!r}) was used, but no label given!"
                                       .format(**locals()), code="invalid")
        if len(lbl) > 80:
            raise QueryValidationError("Label too long: {lbl!r}".format(**locals()), code="invalid")

        if not len(query):
            raise QueryValidationError("Invalid label (before the {label_delimiter})."
                                       .format(**locals()), code="invalid")

        return SearchQuery(q.strip(), label=lbl.strip())

    def __repr__(self):
        return "SearchQuery(label=%s)" % self.label

    def __str__(self):
        return self.label


class QueryValidationError(ValidationError):
    # ugly hack inspired on https://github.com/django/django/commit/a8f4553aaecc7bc6775e0fd54f8c615c792b3d97

    def __init__(self, message, code=None, params=None):
        """
        ValidationError can be passed any object that can be printed (usually
        a string), a list of objects or a dictionary.
        """
        Exception.__init__(self, message, code, params)
        if isinstance(message, dict):
            self.error_dict = message
        elif isinstance(message, list):
            self.error_list = message
        else:
            self.code = code
            self.params = params
            self.message = message
            self.error_list = [self]


def get_date_filters(start_date, end_date, on_date, datetype):
    """
    Yield tuples of (filter_field, filter_value) for given start_date, end_date,
    on_date and datetype, which can be passed to elastic.

    @type start_date: datetime.date
    @type end_date: datetime.date
    @type on_date: datetime.date
    @type datetype: str
    """
    if datetype == 'on':
        yield ('start_date', on_date.isoformat())
        yield ('end_date', (on_date + relativedelta(days=1)).isoformat())

    elif datetype == 'between':
        yield 'start_date', start_date
        yield 'end_date', end_date

    elif datetype == 'after':
        yield 'start_date', start_date

    elif datetype == 'before':
        yield 'end_date', end_date

    # No filter given.


def _clean(s):
    if s is None: return
    s = str(s)
    s = strip_accents(s)
    s = re.sub("[<>+*]", " ", s)
    s = re.sub("\s+", " ", s)
    return s.strip()


def _resolve_recursive(codebook, tree_item, rlanguage):
    this = codebook.get_code(tree_item.code_id).get_label(rlanguage)

    if this is not None:
        yield this

    for t in tree_item.children:
        for child in _resolve_recursive(codebook, t, rlanguage):
            yield child


def resolve_reference(reference, recursive, queries, codebook=None, labels=None, rlanguage=None):
    # Case 1: reference is numeric, so it refers to a Code
    if reference.isnumeric():
        code = codebook.get_code(int(reference))
        if recursive:
            tree = codebook.get_tree(roots=[code])
            tree = list(_resolve_recursive(codebook, tree[0], rlanguage))
            return " OR ".join(tree)
        return code.get_label(rlanguage)

    # Case 2: reference refers to labeled subquery
    if reference in queries:
        # This refernce might contain references, resolve it first.
        return resolve_query(
            queries[reference],
            queries, codebook, labels
        ).query

    # Case 3: reference refers to code in codebook, refered to by its label
    try:
        log.debug("Finding {reference} in {rlanguage} in {labels}, rec={recursive}".format(**locals()))
        code = labels[reference]

        if recursive:
            tree = codebook.get_tree(roots=[code])
            log.warn("Tree: {tree}".format(**locals()))
            tree = list(_resolve_recursive(codebook, tree[0], rlanguage))
            return " OR ".join(tree)
        else:
            return code.get_label(rlanguage)
    except Label.DoesNotExist:
        raise QueryValidationError(
            "Code with label '{reference}' has no label in replacement-language."
            .format(**locals()), code="invalid"
        )
    except KeyError:
        raise QueryValidationError(
            "No code with label '{reference}' found in {codebook}"
            .format(**locals()), code="invalid"
        )
    except TypeError as e:
        log.warn(reference)
        raise QueryValidationError(
            "<{reference}> does not refer to either a code or a query-label. "
            "Did you forget to set a codebook?".format(**locals()), code="invalid"
        )


def resolve_query(query, queries, codebook=None, labels=None, rlanguage=None):
    """
    Take a query and parse and solve all references, marked as <reference>. Each
    query can contain three types of references:

      1) A reference to a previously defined subquery (<[a-zA-Z0-9]+>)
      2a) A reference to a code in the given codebook by id
      2b) A reference to a code in the given codebook by label

    @type query: SearchQuery
    @type queries:
    """
    for mo in REFERENCE_RE.finditer(query.query):
        recursive = bool(mo.group("recursive"))
        reference = mo.group("reference")
        replacement = resolve_reference(
            reference, recursive, queries,
            codebook, labels, rlanguage
        )
        if not replacement:
            raise QueryValidationError("Empty replacement: {query.label}: {query.query} -> {replacement!r}".format(**locals()))

        query.query = query.query.replace(mo.group(0), "(%s)" % replacement, 1)

    return query

def try_get_label(code, label_language):
    try:
        return code.get_label(label_language)
    except Label.DoesNotExist:
        return None

def resolve_queries(queries, codebook=None, label_language=None, replacement_language=None):
    log.warn("Resolving queries {queries}, {codebook}:{label_language} -> {replacement_language}".format(**locals()))

    _queries = {}
    for q in queries:
        if not q.declared_label:
            continue

        label = q.declared_label
        if label.startswith("_"):
            label = label[1:]

        if label in _queries:
            raise ValidationError("Duplicate label: {label}".format(**locals()))

        _queries[label] = q

    labels = None

    if codebook is not None:
        labels = {label: c for label, c in ((try_get_label(c, label_language), c) for c in codebook.get_codes()) if label is not None}

    for query in queries:
        yield resolve_query(query, _queries, codebook, labels, replacement_language)
