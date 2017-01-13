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
import regex
import iso8601

from collections import ChainMap
from typing import Iterable, Any, Union, Sequence, Dict, Tuple, List
from typing import Optional

from django.conf import settings
from django.db.models import QuerySet
from amcat.models import get_used_properties_by_articlesets, ArticleSet, Project
from amcat.tools import queryparser
from amcat.tools import toolkit
from amcat.tools.amcates import get_filter_clause, ALL_FIELDS, ES, get_property_primitive_type
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
    tokens = [token for token in TOKENIZER.split(original_text) if token]
    delimiters = TOKENIZER_INV.split(original_text)
    highlighted_tokens = zip(*(tokenize_highlighted_text(text, marker) for text, marker in zip(highlighted_texts, markers)))

    # If first delimiter is empty, we did not start with empty space. If it is not empty, we did
    # start with some white space. Either way, yield the delimiter.
    yield delimiters.pop(0)

    for token, highlighted in zip(tokens, highlighted_tokens):
        for token_highlighted, marker in zip(highlighted, markers):
            if token_highlighted:
                token = "<{marker}>{token}</{marker}>".format(marker=marker, token=token)

        # yield marked (or unmarked) token
        yield token

        # yield space in between
        yield delimiters.pop(0)


def merge_highlighted_document(texts: Dict[str, str], highlighted_texts: Sequence[Dict[str, str]], markers=Sequence[str]) -> Iterable[Tuple[str, str]]:
    for field in texts.keys():
        texts_and_markers = [(h[field], m) for h, m in zip(highlighted_texts, markers) if field in h]
        if not texts_and_markers:
            yield field, texts[field]
        else:
            yield field, "".join(merge_highlighted(texts[field], *zip(*texts_and_markers)))


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
    for key in list(d.keys()):
        d[key] = d[key][0]


class ESQuerySet:
    """
    Provides a Django-like way of querying documents.
    """
    # Use slots to use tracking down bugs due to wrongly implement copy logic:
    __slots__ = (
        "articlesets", "used_properties", "filters", "ordering", "seed",
        "fields", "highlights", "track_scores", "_count_cache", "_query"
    )

    def __init__(self, articlesets: QuerySet):
        """
        @param articlesets: articlesets to consider articles from
        @param seed: seed used for random ordering
        """
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

    def _do_query(self, query):
        return ES().search(query)

    def __iter__(self) -> Iterable[ESArticle]:
        if not self.highlights:
            # Case 1: no highlighters
            hits = ES().search(self.get_query())["hits"]["hits"]
            for hit in hits:
                _to_flat_dict(hit["fields"])
                yield ESArticle(self.fields, hit["fields"])
        else:
            # Case 2: at least one highlighter present. We need to execute a query for every
            # highlighter plus one for the original text.
            original_texts = self._do_query(self.get_query())["hits"]["hits"]
            for hit in original_texts:
                _to_flat_dict(hit["fields"])

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
                highlighted = [h.get(text["_id"], text["fields"]) for h in highlighted_texts]
                merged = dict(merge_highlighted_document(text["fields"], highlighted, markers))
                yield HighlightedESArticle(self.fields, ChainMap(merged, text["fields"]))

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
        aset_ids = [aset.id for aset in self.articlesets]

        query = {
            "track_scores": True if "?" in self.ordering else self.track_scores,
            "fields": tuple(set(self.fields) | {"_doc"}),
            "query": {
                "function_score": {
                    "query": {
                        # Using filtered allows us to combine a filter context (boolean query) with
                        # a query context (allowing highlighting and scoring)
                        "filtered": {
                            "filter": [
                                get_filter_clause("sets", "in", aset_ids)
                            ]
                        },
                    },
                    "random_score": {
                        "seed": self.get_seed()
                    }
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

            query["fields"] = ("id",)

            # Highlighting is a bit tricky: the query needs to filter on *all* available fields
            # on the document, but the highlighter can only work on specific fields. We therefore
            # specify the query as a filter and the highlighter on specific fields
            query["query"]["function_score"]["query"]["filtered"]["filter"].append(highlight.query.get_dsl())
            query["query"]["function_score"]["query"]["filtered"]["query"] = {
                "query_string": {
                    "fields": highlight.fields,
                    "query": highlight.query_raw
                }
            }

            for field in highlight.fields:
                query["highlight"]["fields"][field] = {"no_match_size": 100}

            if self._query:
                # Add query as filter if we are highlighting
                query["query"]["function_score"]["query"]["filtered"]["filter"].append(self._query.get_dsl())
        elif self._query:
            # No highlighter present, only a query
            query["query"]["function_score"]["query"]["filtered"]["query"] = self._query.get_dsl()

        # Filters do not calculate scores. On filter is always present (due to filtering
        # on articlesets), so we can safely extend the list even if the user specified
        # no filters
        query["query"]["function_score"]["query"]["filtered"]["filter"].extend(self.filters)

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

    def highlight(self, query: str, fields: Sequence[str]=(), mark="mark%i", add_filter=False) -> "ESQuerySet":
        """
        Use a query to highlight terms in a document.

        :param query: Lucene DSL query
        :param fields: fields to highlight
        :param mark: html tag to use. %i will be replaced by a number to account for multiple queries.
        :param add_filter: Indicates whether you also want to *filter* documents on this highlight. If True, only
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
