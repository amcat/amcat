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
Utility module for keyword searches
TODO: NOTE: This module replaces the old 'solrlib', but I wonder whether it can be removed
# entirely. The 'getTable' / 'getArticles' can move either to their respective
# webscripts, or to the REST API. The form handling should just go to the form.
(but then I started moving things from the form to here...)
"""

from __future__ import unicode_literals, print_function, absolute_import

from django.db import models
import collections
import logging
from amcat.tools.amcates import ES
from amcat.tools.table import table3
from amcat.models import Medium, Label
import re
from amcat.tools.toolkit import stripAccents,readDate
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from amcat.models import Project
from amcat.tools.progress import NullMonitor

log = logging.getLogger(__name__)

def _get_filter_date(cleaned_data, prop):
    if prop not in cleaned_data: return "*"
    return cleaned_data[prop].isoformat() + "Z"

FILTER_FIELDS = {"mediums" : "mediumid", "article_ids" : "ids", "articlesets" : "sets"}

def _serialize(x):
    if isinstance(x, (str, unicode)):
        return x
    if isinstance(x, collections.Iterable):
        return [_serialize(e) for e in x]
    elif isinstance(x, models.Model):
        return x.id
    return x

def filters_from_form(form_data):
    if form_data.get('datetype') == 'on':
        d = readDate(form_data.get('on_date'))
        yield 'start_date', d.isoformat()
        yield 'end_date', (d + relativedelta(days=1)).isoformat()
    elif form_data.get('datetype') == 'between':
        yield 'start_date', form_data.get('start_date')
        yield 'end_date', form_data.get('end_date')
    elif form_data.get('datetype') == 'after':
        yield 'start_date', form_data.get('start_date')
    elif form_data.get('datetype') == 'before':
        yield 'end_date', form_data.get('end_date')


    for k in form_data.keys():
        if  k in FILTER_FIELDS:
            try:
                vals = form_data.getlist(k)
            except AttributeError:
                vals = form_data[k]
                # make sure vals is a list
                if isinstance(vals, (str, unicode)) or not isinstance(vals, collections.Iterable):
                    vals = [vals]
            vals = [_serialize(v) for v in vals if v]
            if vals:
                yield FILTER_FIELDS[k], vals

    if 'articlesets' not in form_data:
        # filter on all sets in project
        p = Project.objects.get(pk=form_data['projects'])
        sets = [s.id for s in p.all_articlesets()]
        yield "sets", sets



def getDatatable(form, rowlink='article/{id}', **kwargs):
    from api.rest.datatable import Datatable
    from api.rest.resources import SearchResource
    table = Datatable(SearchResource, rowlink=rowlink, **kwargs)

    for field, val in filters_from_form(form):
        table = table.filter(**{field : val})

    for query in queries_from_form(form):
        table = table.add_arguments(q=query.query)

    if form.get('include_all') and form.get('include_all') != 'False':
        table = table.add_arguments(q="*")
    return table

def get_ids_per_query(form):
    """
    Return a sequence of label, list-of-ids pairs per query
    """
    filters = dict(filters_from_form(form))
    queries = list(queries_from_form(form))
    for q in queries:
        result = list(ES().query_ids(query=q.query, filters=filters))
        yield q.label, result

def get_ids(form):
    """Return a list of article ids matching this form"""
    filters = dict(filters_from_form(form))
    queries = list(queries_from_form(form))
    if queries:
        query = "\n".join("({q.query})".format(**locals()) for q in queries)
    else:
        query = None

    return ES().query_ids(query=query, filters=filters)

def getArticles(form, **kargs):
    fields = ['mediumid', 'date', 'headline', 'medium']

    sort = form.get('sortColumn', None)

    if 'keywordInContext' in form['columns']:
        raise NotImplementedError()

    query = query_from_form(form)

    kargs["highlight" if query else "lead"] = True

    filters = dict(filters_from_form(form))

    log.info("Query: {query!r}, with filters: {filters}".format(**locals()))


    score = 'hits' in form['columns']
    result = list(ES().query(query, filters=filters, fields=fields, sort=sort, score=score, **kargs))

    if 'hits' in form['columns']:
        # add hits columns
        def add_hits_column(r):
            r.hits = {q.label : 0 for q in form['queries']}
            return r

        result_dict = {r.id : add_hits_column(r) for r in result}
        f = dict(ids=list(result_dict.keys()))

        for q in queries_from_form(form):
            for hit in ES().query(q.query, filters=f, fields=[]):
                result_dict[hit.id].hits[q.label] = hit.score

    return result

def getTable(form, progress_monitor=NullMonitor):
    table = table3.DictTable(default=0)
    table.rowNamesRequired = True
    dateInterval = form['dateInterval']
    group_by = form['xAxis']
    if group_by == "medium": group_by = "mediumid"
    filters = dict(filters_from_form(form))

    queries = list(queries_from_form(form))
    query = query_from_form(form)

    yAxis = form['yAxis']
    if yAxis == 'total':
        _add_column(table, 'total', query, filters, group_by, dateInterval)
        progress_monitor.update(90, "Got results")
    elif yAxis == 'medium':
        media = Medium.objects.filter(pk__in=ES().list_media(query, filters)).only("name")

        for medium in sorted(media):
            filters['mediumid'] = medium.id
            name = u"{medium.id} - {}".format(medium.name.replace(",", " ").replace(".", " "), **locals())
            _add_column(table, name, query, filters, group_by, dateInterval)
            progress_monitor.update(90 / len(media), "Got results for medium {medium.id}".format(**locals()))
    elif yAxis == 'searchTerm':
        for q in queries:
            _add_column(table, q.label, q.query, filters, group_by, dateInterval)
            progress_monitor.update(90 / len(queries), "Got results for {q.label!r}".format(**locals()))
    else:
        raise Exception('yAxis {yAxis} not recognized'.format(**locals()))

    table.queries = queries
    return table

def add_medium_names(result):
    "Change medium ids to medium names"
    result = list(result)
    ids = {group for (group, n) in result}
    media = dict(Medium.objects.filter(pk__in=ids).values_list("pk", "name"))
    for mid, n in result:
        label = "{mid} - {name}".format(name=media[mid], **locals())
        yield label, n


def _add_column(table, column_name, query, filters, group_by, dateInterval):
    if group_by == "total":
        n = ES().count(query, filters)
        table.addValue("Total", column_name, n)
    else:
        results = ES().aggregate_query(query, filters, group_by, dateInterval)
        if group_by == "mediumid":
            results = add_medium_names(results)

        for group, n in results:
            table.addValue(unicode(group), column_name, n)
    table.columnTypes[column_name] = int


def get_total_n(form):
    query = query_from_form(form)
    filters = dict(filters_from_form(form))
    return ES().count(query, filters)

def get_statistics(form):
    query = query_from_form(form)
    filters = dict(filters_from_form(form))
    return ES().statistics(query, filters)

class QueryError(Exception):
    pass


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

def _clean(s):
    if s is None: return
    s = unicode(s)
    s = stripAccents(s)
    s = re.sub("[<>+*]"," ", s)
    s = re.sub("\s+"," ", s)
    return s.strip()

class SearchQuery(object):
    """
    Represents a query object that contains both a query and
    an optional label
    """
    def __init__(self, query, label=None):
        self.query = stripAccents(query)
        self.declared_label = _clean(label)
        self.label = self.declared_label or _clean(self.query)


    @classmethod
    def _get_label_delimiter(cls, query_string, label_delimiters):
        for d in label_delimiters:
            if d in query_string:
                return d

    @classmethod
    def from_string(cls, query_string, label_delimiters=("#\t|")):
        """
        Returns a SearchQuery object, parsed from string `q`
        @raises: ValidationError if `q` is not valid query
        """
        query = query_string.strip()
        label_delimiter = cls._get_label_delimiter(query_string, label_delimiters)

        if label_delimiter:
            label_delimiter = label_delimiter[0]
            pattern = label_delimiter.replace("|", "\\|") + "+"
            lbl, q = re.split(pattern, query, 1)

            if len(lbl) == 0:
                raise QueryValidationError("Delimiter ({label_delimiter!r}) was used, but no label given!"
                                      "Query was: {query!r}".format(**locals()), code="invalid")
            if len(lbl) > 80:
                raise QueryValidationError("Label too long: {lbl!r}".format(**locals()), code="invalid")
            if not len(query):
                raise QueryValidationError("Invalid label (before the {label_delimiter}). Query was: {query!r}"
                                      .format(**locals()), code="invalid")
            return SearchQuery(q.strip(), label=lbl.strip())

        return SearchQuery(query)

def queries_from_form(form):
    """
    Returns a sequence of SearchQuery objects taken from the form['query'] field
    """
    if form['query']:
        #HACK: clean doesn't get called with delayed webscripts, webscripts need overhaul!
        from amcat.models import Codebook, Language
        cb, lbl, rep = [form.get(x) for x in ['codebook', 'codebook_label_language', 'codebook_replacement_language']]
        if not cb:
            cb = None
        elif isinstance(cb, (int, unicode)):
            cb = Codebook.objects.get(pk=int(cb))
        if lbl and isinstance(lbl, (int, unicode)): lbl = Language.objects.get(pk=int(lbl))
        if rep and isinstance(rep, (int, unicode)): rep = Language.objects.get(pk=int(rep))
        if cb: cb.cache_labels()

        log.warn("X {cb}:{lbl}->{rep}".format(**locals()))

        queries = [SearchQuery.from_string(line)
                   for line in form['query'].split("\n")
                   if line.strip()]
        resolved = resolve_queries(queries, codebook=cb, label_language=lbl, replacement_language=rep)

        resolved = list(resolved)
        return (q for q in resolved if not q.label.startswith("_"))
    else:
        return []

def query_from_form(form):
    queries = list(queries_from_form(form))
    if queries:
        return u' OR '.join(u'({q.query})'.format(**locals()) for q in queries)

def _resolve_recursive(codebook, tree_item, rlanguage):
    this = codebook.get_code(tree_item.code_id).get_label(rlanguage, fallback=False)

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
        return code.get_label(rlanguage, fallback=False)

    # Case 2: reference refers to labeled subquery
    if reference in queries:
        # This refernce might contain references, resolve it first.
        return resolve_query(
            queries[reference],
            queries, codebook, labels
        ).query

    # Case 3: reference refers to code in codebook, refered to by its label
    try:
        log.warn("Finding {reference} in {rlanguage} in {labels}, rec={recursive}".format(**locals()))
        code = labels[reference]

        if recursive:
            tree = codebook.get_tree(roots=[code])
            log.warn("Tree: {tree}".format(**locals()))
            tree = list(_resolve_recursive(codebook, tree[0], rlanguage))
            return " OR ".join(tree)
        else:
            return code.get_label(rlanguage, fallback=False)
    except Label.DoesNotExist:
        raise QueryValidationError("Code with label '{reference}' has no label in replacement-language."
                              .format(**locals()), code="invalid")
    except KeyError:
        raise QueryValidationError("No code with label '{reference}' found in {codebook}"
                              .format(**locals()), code="invalid")
    except TypeError:
        log.warn(reference)
        raise QueryValidationError("<{reference}> does not refer to either a code or a query-label. "
                            "Did you forget to set a codebook?".format(**locals()), code="invalid")

    if not recursive:
        return label

    return resolve_reference(
        unicode(labels[reference].id), recursive,
        queries, codebook, labels, rlanguage
    )

REFERENCE_RE = re.compile(r"<(?P<reference>.*?)(?P<recursive>\+?)>")

def resolve_query(query, queries, codebook=None, labels=None, rlanguage=None):
    """
    Take a query and parse and solve all references, marked as <reference>. Each
    query can contain three types of references:

      1) A reference to a previously defined subquery (<[a-zA-Z0-9]+>)
      2) A reference to a code in the given codebook

    """
    for mo in REFERENCE_RE.finditer(query.query):
        recursive = bool(mo.group("recursive"))
        reference = mo.group("reference")
        replacement = resolve_reference(
            reference, recursive, queries,
            codebook, labels, rlanguage
        )
        if not replacement:
            raise QueryError("Empty replacement: {query.label}: {query.query} -> {replacement!r}".format(**locals()))

        replacement = "(" + replacement + ")"
        query.query = query.query.replace(mo.group(0), replacement, 1)

    return query


def resolve_queries(queries, codebook=None, label_language=None, replacement_language=None):
    log.warn("Resolving queries {queries}, {codebook}:{label_language} -> {replacement_language}".format(**locals()))
    _queries = {}
    for q in queries:
        if not q.declared_label: continue
        label = q.declared_label
        if label.startswith("_"): label = label[1:]
        if label in _queries:
            raise ValidationError("Duplicate label: {label}".format(**locals()))
        _queries[label] = q

    labels = None
    if codebook is not None:
        labels = { c.get_label(label_language, fallback=False) : c for c in codebook.get_codes() }
    else:
        labels = None

    for query in queries:
        q = resolve_query(query, _queries, codebook, labels, replacement_language)
        if q:
            yield q


###########################################################################
#                          U N I T   T E S T S                            #
###########################################################################

from amcat.tools import amcattest

class TestKeywordSearch(amcattest.AmCATTestCase):

    def test_get_label_delimiter(self):
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "a"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ab"), "a")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "ba"), "b")
        self.assertEquals(SearchQuery._get_label_delimiter("abc", "d"), None)
