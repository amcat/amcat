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
import datetime
import functools
import random
import collections
import regex
import html
import iso8601

from collections import ChainMap
from typing import Iterable, Any, Union, Sequence, Dict, Tuple, List
from typing import Optional

from django.conf import settings
from django.db.models import QuerySet
from django.http import QueryDict

from amcat.models import get_used_properties_by_articlesets, ArticleSet, Project
from amcat.tools import queryparser
from amcat.tools import toolkit
from amcat.tools.amcates import ALL_FIELDS, ES, get_property_primitive_type
from amcat.tools.queryparser import Term


TOKEN_START = toolkit.random_alphanum(16)
TOKENIZER_PATTERN = settings.ES_SETTINGS["analysis"]["tokenizer"]["unicode_letters_digits"]["pattern"]
TOKENIZER_INV = regex.compile(TOKENIZER_PATTERN.replace("^", "") + "+")
TOKENIZER = regex.compile(TOKENIZER_PATTERN)


def tokenize_highlighted_text(text: str, marker: str):
    start_marker = "<{}>".format(marker)
    stop_marker = "</{}>".format(marker)

    # Get rid of html tags. Instead, replace them by unique tokens
    text = text.replace(start_marker, TOKEN_START).replace(stop_marker, "")

    for token in TOKENIZER.split(text):
        if token:
            yield token.startswith(TOKEN_START)


def merge_highlighted(original_text, highlighted_texts: Sequence[str], markers: Sequence[str]):
    """

    """
    tokens = [html.escape(token) for token in TOKENIZER.split(original_text) if token]
    delimiters = TOKENIZER_INV.split(original_text)
    highlighted_tokens = zip(*(tokenize_highlighted_text(text, marker) for text, marker in zip(highlighted_texts, markers)))

    # If first delimiter is empty, we did not start with empty space. If it is not empty, we did
    # start with some white space. Either way, yield the delimiter.
    yield html.escape(delimiters.pop(0))

    for token, highlighted in zip(tokens, highlighted_tokens):
        for token_highlighted, marker in zip(highlighted, markers):
            if token_highlighted:
                token = "<{marker}>{token}</{marker}>".format(marker=marker, token=token)

        # yield marked (or unmarked) token
        yield token

        # yield space in between
        yield html.escape(delimiters.pop(0))


def merge_highlighted_document(texts: Dict[str, str], highlighted_texts: Sequence[Dict[str, str]], markers=Sequence[str]) -> Iterable[Tuple[str, str]]:
    for field in texts.keys():
        texts_and_markers = [(h[field], m) for h, m in zip(highlighted_texts, markers) if field in h]
        if not texts_and_markers:
            yield field, texts[field]
        else:
            yield field, "".join(merge_highlighted(texts[field], *zip(*texts_and_markers)))


def _to_list(ptype, filter_value):
    if isinstance(filter_value, str):
        filter_value = filter_value.split(",")
    return [ptype(v) for v in filter_value]


def get_filter_clause_str(field: str, qualifier: Optional[str], filter_value):
    if qualifier is None:
        return {"terms": {field: str(filter_value)}}
    elif qualifier == "in":
        return {"terms": {field: _to_list(str, filter_value)}}
    elif qualifier == "exact":
        return {"match": {"{}.raw".format(field): filter_value}}
    elif qualifier == "exact__in":
        return {"match": {"{}.raw".format(field): filter_value}}
    else:
        raise ValueError("Did not recognize qualifier {!r} on str field {!r}.".format(qualifier, field))


def get_filter_clause_num(field: str, qualifier: Optional[str], filter_value, ptype):
    if qualifier is None:
        return {"term": {field: ptype(filter_value)}}
    elif qualifier == "in":
        return {"terms": {field: _to_list(ptype, filter_value)}}
    elif qualifier in ("lte", "gte", "lt", "gt"):
        return {"range": {field: {qualifier: filter_value}}}
    else:
        raise ValueError("Did not recognize qualifier {!r} on numeric field {!r}.".format(qualifier, field))


def get_filter_clause_date(field: str, qualifier: Optional[str], filter_value):
    if qualifier != "in":
        filter_value = [filter_value]

    # If given a datetime the filter value must either be a datetime object or
    # an iso8601 conforming string
    parsed_values = []
    for v in filter_value:
        if not isinstance(v, datetime.datetime):
            try:
                parsed_values.append(iso8601.parse_date(v, default_timezone=None))
            except iso8601.ParseError:
                raise ValueError("Value of {}, {}, is not an iso8601 string or datetime".format(field, v))
        else:
            parsed_values.append(v)

    filter_value = list({v.isoformat() for v in parsed_values})
    if qualifier != "in":
        filter_value = filter_value[0]

    if qualifier is None or qualifier == "in":
        # Match exactly
        return {"terms": {field: filter_value}}
    elif qualifier == "on":
        # Match all articles on given date
        return {"range": {field: {"gte": filter_value + "||/d", "lt": filter_value + "||+1d/d"}}}
    elif qualifier in ("lte", "gte", "lt", "gt"):
        return {"range": {field: {qualifier: filter_value}}}
    else:
        raise ValueError("Did not recognize qualifier {!r} on date field.".format(qualifier))


def get_filter_clause_sets(field: str, qualifier: Optional[str], filter_value):
    if qualifier == "overlap":
        return {"terms": {field: list(filter_value)}}

    error = "{!r} not a valid qualifier. Choose from: overlap. Example: filter({}__overlap={}"
    raise ValueError(error.format(qualifier, field, filter_value))


def get_filter_clause(field: str, qualifier: Optional[str], filter_value):
    """

    @param field:
    @param qualifier:
    @param filter_value:
    @return:
    """
    ptype = get_property_primitive_type(field)

    if ptype == datetime.datetime:
        return get_filter_clause_date(field, qualifier, filter_value)
    elif ptype == int or ptype == float:
        return get_filter_clause_num(field, qualifier, filter_value, ptype)
    elif ptype == str:
        return get_filter_clause_str(field, qualifier, filter_value)
    elif ptype == set:
        return get_filter_clause_sets(field, qualifier, filter_value)
    else:
        raise ValueError("Did not recognize primitive type {} of field {}".format(ptype, field))


def _get_filter_clauses_from_querydict(qdict: QueryDict):
    filters = {}
    for field in qdict:
        if "__" in field:
            field_name, qualifier = field.split("__", 1)

            if qualifier == "in":
                # If user specifies multiply ins, take intersection
                value = [v.strip() for v in qdict.get(field).split(",")]
                if len(qdict.getlist(field)) > 1:
                    for values in qdict.getlist(field):
                        value = set(value) & {v.strip() for v in values.split(",")}
                    value = list(value)
            elif len(qdict.getlist(field)) > 1:
                raise ValueError("Is does not make sense to have more than 1 value for filter: {}".format(field))
            else:
                value = qdict.get(field)
        else:
            value = list(qdict.getlist(field))
            field += "__in"

        if field in filters:
            # Field has already been filtered with a different qualifier
            filters[field] = list(set(filters[field]) & set(value))
        else:
            filters[field] = value
    return filters


def get_filter_clauses_from_querydict(qdict: QueryDict):
    """
    Given a querydict, calculate filters given to amcates
    """
    return get_filter_clauses(**_get_filter_clauses_from_querydict(qdict))


def get_filter_clauses(**filters):
    """
    Build elastic filter, based on Django like filters. Values can be given as strings, even if
    their associated field is not a string field. Dates should adhere to ISO8601 however, while
    ints and floats need to be able to be parsed by their respective Python builtin functions.

    Examples:

        >>> get_filter_clauses(date="2011-01-01")
        {"match": {"date": "2011-01-01T00:00:00"}}
        >>> get_filter_clauses(date__gte="2011-01-01")
        {"range": {"date": {"gte": "2011-01-01T00:00:00||/d"}}}
        >>> get_filter_clauses(date__on=datetime.datetime(2011, 1, 1))
        {"range": {"date": {"gte": "2011-01-01T00:00:00||/d", "lt": "2011-01-01T00:00:00||+1d/d"}}}
        >>> get_filter_clauses(length_int=10)
        {"match": {"length_int": 10}}
        >>> get_filter_clauses(length_int__in=[10, 20])
        {"match": {"length_int": {10, 20}}}
        >>> get_filter_clauses(length_int__in=["10", "20"])
        {"match": {"length_int": {10, 20}}}
        >>> get_filter_clauses(length_int__gte=10)
        {"range": {"length_int": {"gte": 10}}}
    """
    # TODO: Remove these checks as soon as callers are fixed
    for field in ("start_date", "end_date", "on_date"):
        if field in filters:
            raise ValueError("Do not pass {}. Use date, date__gt, date__lt instead.")

    for field in ("hashes",):
        if field in filters:
            raise ValueError("Do not pass plurals: {}. Use field__in instead.".format(field))

    for field in ("project", "projectid"):
        if field in filters:
            raise ValueError("Do not pass plurals: {}. Use field__in instead.".format(field))

    for field, filter_value in filters.items():
        if "__" in field:
            field_name, qualifier = field.split("__", 1)
        else:
            field_name = field
            qualifier = None

        yield get_filter_clause(field_name, qualifier, filter_value)


class ESArticle:
    def __init__(self, fields, result):
        self._fields = fields
        self._result = result

    def __getattr__(self, field):
        if field in self._fields:
            value = None
            if field in self._result:
                value = self._result[field]
                if get_property_primitive_type(field) == datetime.datetime:
                    value = iso8601.parse_date(value, default_timezone=None)
            setattr(self, field, value)
            return value
        raise AttributeError("{!r} object has no attribute {!r}".format(self, field))

    def to_dict(self):
        return {field: getattr(self, field) for field in self._fields}

    def __repr__(self):
        map_repr = ", ".join("{!r}: {!r}".format(field, getattr(self, field)) for field in self._fields)
        return "<{}({{{}}})>".format(self.__class__.__name__, map_repr)


class HighlightedESArticle(ESArticle):
    def get_non_highlighted(self) -> ESArticle:
        return ESArticle(self._fields, self._result.maps[1])


def replace_keys(dsl: dict, key: str, replacement: str):
    for value in dsl.values():
        if isinstance(value, dict):
            replace_keys(value, key, replacement)

    if key in dsl:
        dsl[replacement] = dsl.pop(key)


class Highlight:
    def __init__(self, fields: Sequence[str], query: str, mark: str):
        self.query_raw = query
        self.query = queryparser.parse_to_terms(query)  # type: Term
        self.fields = fields
        self.mark = mark


def _to_flat_dict(d: Dict[str, List[Any]]):
    for k, v in list(d.items()):
        if v is not None and isinstance(v, list) and v:
            d[k] = v[0]


class ESQuerySet:
    """
    Provides a Django-like way of querying documents.
    """
    # Use slots to use tracking down bugs due to wrongly implement copy logic:
    __slots__ = (
        "articlesets", "used_properties", "filters", "ordering", "seed",
        "fields", "highlights", "track_scores", "_count_cache", "_query",
        "size", "offset"
    )

    def __init__(self, articlesets: Optional[QuerySet]=None):
        """
        @param articlesets: articlesets to consider articles from
        @param seed: seed used for random ordering
        """
        if articlesets is None:
            self.articlesets = ArticleSet.objects.all().only("id")
            self.used_properties = ES().get_properties()
        else:
            self.articlesets = articlesets.only("id")
            self.used_properties = ALL_FIELDS | frozenset(get_used_properties_by_articlesets(self.articlesets))

        self.filters = ()
        self.ordering = ()
        self.seed = None
        self.fields = ("id", "title", "date")
        self.highlights = ()
        self.track_scores = False
        self._query = None
        self._count_cache = None

        # HACK: Set size to default max of elastic. We should think about pagination..
        self.size = 10000
        self.offset = 0

    def _do_query(self, query):
        result = ES().search(query)

        if len(result["hits"]["hits"]) == self.size:
            raise NotImplementedError("Returned 10000 articles exactly. Time to implement scroll :)")

        return result

    def __iter__(self) -> Iterable[ESArticle]:
        if not self.highlights:
            # Case 1: no highlighters
            hits = ES().search(self.get_query())["hits"]["hits"]
            for hit in hits:
                _to_flat_dict(hit["_source"])
                yield ESArticle(self.fields, hit["_source"])
        else:
            # Case 2: at least one highlighter present. We need to execute a query for every
            # highlighter plus one for the original text.
            original_texts = self._do_query(self.get_query())["hits"]["hits"]
            for hit in original_texts:
                _to_flat_dict(hit["_source"])

            # Order might be unreliable, so we make mappings
            unordered = self.order_by(None)
            highlighted_texts = []
            for highlight in self.highlights:
                unordered.get_query(highlight)
                result = self._do_query(self.get_query(highlight))
                for hit in result["hits"]["hits"]:
                    _to_flat_dict(hit["highlight"])
                highlighted_texts.append({d["_id"]: d["highlight"] for d in result["hits"]["hits"]})

            markers = [h.mark for h in self.highlights]
            for text in original_texts:
                highlighted = [h.get(text["_id"], text["_source"]) for h in highlighted_texts]
                merged = dict(merge_highlighted_document(text["_source"], highlighted, markers))
                yield HighlightedESArticle(self.fields, ChainMap(merged, text["_source"]))

    @functools.lru_cache()
    def __len__(self):
        """For a more efficient way of determining this size of this set use count(). This
        method will execute the query (which includes fetching all documents) and count
        the size of that set.

        This method is left 'inefficient' due to the following common pattern:

            qs = list(ESQuerySet(...))

        list() will first determine the size of its given argument (if it detects __len__)
        to allocate a sufficient amount of memory. Therefore; if we would call count() we
        would execute the query twice which is clearly undesirable.
        """
        if self._count_cache:
            return self._count_cache
        return sum(1 for _ in self)

    def __bool__(self):
        return bool(len(self))

    def __getitem__(self, item: Union[int, slice]):
        # TODO: Query elastic for pagination
        if isinstance(item, int):
            if item < 0:
                raise TypeError("Negative indexing not supported")

            for i, article in enumerate(self):
                if i == item:
                    return article
            raise IndexError("IndexError: list index out of range")

        start, stop, step = item
        start = start or 0
        stop = len(self) if stop is None else stop
        step = 1 if step is None else step

        if start < 0 or stop < 0:
            raise TypeError("Negative indexing not supported")

        if step <= 0:
            raise TypeError("Step can't be negative or zero")

        articles = []
        for i, article in enumerate(self):
            if i >= stop:
                break
            elif len(articles) % step != 0:
                continue
            elif i >= start:
                articles.append(article)

        return articles

    def _check_fields(self, fields):
        for field in fields:
            if field not in self.used_properties:
                raise ValueError("Field {} not present in selected article sets".format(field))

    def values_list(self, *fields, flat=False) -> Iterable[Any]:
        """Return an iterable of values similar to Django's values_list.

        @param flat: given one field yield a flat list instead of list of one-tuples."""
        if flat and len(fields) != 1:
            raise ValueError("flat=True is only a valid option when specifying one field.")

        new = self._copy(fields=fields)
        if flat:
            return (getattr(r, fields[0]) for r in new)
        else:
            return (tuple(getattr(art, f) for f in fields) for art in new)

    def get_seed(self):
        """Return current seed or, if it doesn't exist, generate a fresh one"""
        if self.seed is None:
            self.seed = random.randint(0, 2**63-1)
        return self.seed

    def set_seed(self, seed: Optional[str]):
        self.seed = seed

    def get_query(self, highlight: Optional[Highlight]=None) -> dict:
        """Return elasticsearch query based on a specific highlighter (or None). A highlighter
        will force a query (if specified) to run as a filter."""
        aset_ids = [aset.id for aset in self.articlesets] if self.articlesets is not None else None
        if aset_ids is None:
            aset_filter = {}
        else:
            aset_filter = {"filter": [get_filter_clause("sets", "overlap", aset_ids)] }

        query = {
            "track_scores": True if "?" in self.ordering else self.track_scores,
            "_source": tuple(set(self.fields) | {"_doc"}),
            "size": self.size,
            "from": self.offset,
            "query": {
                "function_score": {
                    "query": {
                        # instantiate all bool subclauses to empty lists so clauses can be added incrementally
                        "bool": dict({
                            "must": [],
                            "must_not": [],
                            "should": [],
                            "filter": [],
                        }, **aset_filter),
                    } ,
                    "functions": [
                        {"random_score": {"seed": self.get_seed()}}
                    ],
                    "boost_mode": "replace"
                }

            },
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {

                }
            }
        }

        if highlight:
            query["highlight"]["pre_tags"][0] = "<{}>".format(highlight.mark)
            query["highlight"]["post_tags"][0] = "</{}>".format(highlight.mark)

            query["_source"] = ("id",)

            # Highlighting is a bit tricky: the query needs to filter on *all* available fields
            # on the document, but the highlighter can only work on specific fields. We therefore
            # specify the query as a filter and the highlighter on specific fields
            query["query"]["function_score"]["query"]["bool"]["filter"].append(highlight.query.get_dsl())
            query["query"]["function_score"]["query"]["bool"]["must"] = {
                "query_string": {
                    "fields": highlight.fields,
                    "query": highlight.query_raw
                }
            }

            for field in highlight.fields:
                query["highlight"]["fields"][field] = {
                    "no_match_size": 1024*1024*5,  # 5 MiB articles anyone?
                    "number_of_fragments": 0
                }

            if self._query:
                # Add query as filter if we are highlighting
                query["query"]["function_score"]["query"]["bool"]["filter"].append(self._query.get_dsl())
        elif self._query:
            # No highlighter present, only a query
            query["query"]["function_score"]["query"]["bool"]["must"] = self._query.get_dsl()

        # Filters do not calculate scores. On filter is always present (due to filtering
        # on articlesets), so we can safely extend the list even if the user specified
        # no filters
        query["query"]["function_score"]["query"]["bool"]["filter"].extend(self.filters)

        # Sorting
        if self.ordering:
            sort = []
            for order in self.ordering:
                if order == "?":
                    sort.append("_score")
                else:
                    sort.append(dict((order,)))
            query["sort"] = sort

        return query

    def only(self, *fields) -> "ESQuerySet":
        self._check_fields(fields)
        return self._copy(fields=fields)

    def highlight_fragments(self,
                            query: str,
                            fields: Sequence[str],
                            mark="mark",
                            add_filter=False,
                            number_of_fragments=3,
                            fragment_size=150) -> Dict[int, Dict[str, List[str]]]:
        """
        Highlight articles but only return fragments.

        @param query: Lucene query
        @param fields: fields to highlight
        @param mark: html tag to mark highlights.
        @param add_filter: Indicates whether you also want to *filter* documents on this
                            highlight. If True, only documents with highlighting will be
                            returned.
        @param number_of_fragments: Number of fragments to include
        @param fragment_size: size of fragments in characters (bytes/unicode codepoints, not
                              formalized by elasticsearch..)
        @return: A dictionary mapping and article id to a dictionary mappping fieldnames
                 to a list of fragments
        """
        # Pass highlight options to "normal" highlighter, generate default query
        random_mark = toolkit.random_alphanum(20)
        new = self.highlight(query, fields=fields, mark=random_mark, add_filter=add_filter)
        dsl = new.get_query(new.highlights[-1])

        # Set highlight options for fragments
        for field in fields:
            dsl["highlight"]["fields"][field] = {
                "number_of_fragments": number_of_fragments,
                "fragment_size": fragment_size,
                "no_match_size": fragment_size
            }

        # Parse result
        articles = collections.OrderedDict()
        for hit in new._do_query(dsl)["hits"]["hits"]:
            articles[hit["_source"]["id"]] = {
                field: hit["highlight"].get(field, ["-"]) for field in fields
            }

        # HACK: Elastic does not escape html tags *in the article*. We therefore pass a random
        # marker and use it to escape ourselves.
        double_random_mark = random_mark + random_mark
        for article in articles.values():
            for field in list(article.keys()):
                texts = article[field]
                for i, text in enumerate(texts):
                    text = text.replace("<{}>".format(random_mark), random_mark)
                    text = text.replace("</{}>".format(random_mark), double_random_mark)
                    text = html.escape(text)
                    text = text.replace(double_random_mark, "</{}>".format(mark))
                    text = text.replace(random_mark, "<{}>".format(mark))
                    texts[i] = text

        return articles

    def highlight(self,
                  query: str,
                  fields: Sequence[str]=(),
                  mark="mark%i",
                  add_filter=False,
                  ) -> "ESQuerySet":
        """
        Use a query to highlight terms in a document. If any html is present in the document it
        will be escaped. It is therefore safe to insert highlighted fields directly into an HTML
        document.

        @param query: Lucene DSL query
        @param fields: fields to highlight
        @param mark: html tag to use. %i will be replaced by a number to account for multiple queries.
        @param add_filter: Indicates whether you also want to *filter* documents on this highlight. If True, only
                           documents with highlighting will be returned.
        """
        if fields == ():
            fields = self.fields

        # Check fields, add fields if necessary
        self._check_fields(fields)
        new_fields = self.fields
        for field in fields:
            if field not in new_fields:
                new_fields += (field,)

        # Create highlighted ESQuerySet
        highlight = Highlight(fields, query, mark.replace("%i", str(len(self.highlights))))
        new = self._copy(highlights=self.highlights + (highlight,), fields=new_fields)

        # Also add query as filter if user requested so
        if add_filter:
            return new.filter_query(query)

        return new

    def query(self, query: str) -> "ESQuerySet":
        """
        Use a query string to query the final result. If you do not need scoring, use filter_query.

        @param query: query in Lucene syntax
        """
        query_dsl = queryparser.parse_to_terms(query)
        return self._copy(_query=query_dsl)

    def filter_query(self, query: str):
        """
        Filter a queryset using a querystring. This is different from query(), as it will
        not be able to generate highlights or scores. It is quicker, however.
        """
        query_term = queryparser.parse_to_terms(query)
        return self._copy(filters=self.filters + (query_term.get_dsl(),))

    def filter(self, **kwargs) -> "ESQuerySet":
        """
        Filter on a number of fields. Supports Django-like property filtering. See
        get_filter_clauses() in amcates for more information. Examples:

            ex.filter(date__lte="2011-01-01")
            ex.filter(page_num__in=[1, 3, 4])

        """
        # Determine new filters
        new_filters = []
        for field, value in kwargs.items():
            qualifier = None
            if "__" in field:
                field, qualifier = field.split("__", 1)
            self._check_fields((field,))
            new_filters.append(get_filter_clause(field, qualifier, value))

        # Copy self and install new filters
        return self._copy(filters=self.filters + tuple(new_filters))

    def order_by(self, *fields, seed: Optional[int]=None) -> "ESQuerySet":
        """
        Order by a number of fields. By default, order ascending. If a minus is given in front
        of the fieldname, order in a descending manner. Random ordering can be given by passing
        a single question mark. Examples:

            qs.order_by("id")
            qs.order_by("-id")
            qs.order_by("?")
            qs.order_by("date", "id")

        Note that it is not possible to order a single field randomly. You can reset an ordering
        by passing no fields or None explicitly:

            qs.order_by()
            qs.order_by(None)

        If you need a deterministic ordering, but you don't care about the ordering itself use
        _doc as an order field:

            qs.order_by("_doc")

        @param seed: a random ordering can be made deterministic by supplying a seed value.
        """
        if fields == (None,):
            return self._copy(ordering=())

        # Check for validity
        ordering = []
        for field in fields:
            if field == "?" or field == "_doc":
                # Random ordering or deterministic ordering
                ordering.append(field)
                continue

            order = "asc"
            _field = field
            if field.startswith(("+", "-")):
                if field[0] == "-":
                    order = "desc"
                _field = field[1:]

            if get_property_primitive_type(_field) == str:
                raise NotImplementedError("Ordering on string type not yet supported")

            self._check_fields((_field,))
            ordering.append((_field, order))

        # Copy self and return new one
        seed = seed if seed is not None else self.seed
        return self._copy(ordering=tuple(ordering), seed=seed)

    def count(self):
        return ES()._count(self.get_query())["count"]

    def _copy(self, **kwargs):
        new = ESQuerySet(ArticleSet.objects.none())
        for slot in self.__slots__:
            setattr(new, slot, getattr(self, slot))

        for attr, value in kwargs.items():
            setattr(new, attr, value)

        return new

    @classmethod
    def from_project(cls, project: Project, **kwargs):
        return cls(project.all_articlesets(), **kwargs)
