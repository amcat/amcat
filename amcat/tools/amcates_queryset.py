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
import iso8601

from collections import ChainMap
from typing import Iterable, Any, Union
from typing import Optional

from django.db.models import QuerySet
from amcat.models import get_used_properties_by_articlesets, ArticleSet, Project
from amcat.tools import queryparser
from amcat.tools.amcates import get_filter_clause, ALL_FIELDS, ES, get_property_primitive_type
from amcat.tools.queryparser import Term
from amcat.tools.toolkit import random_alphanum


class ESArticle:
    def __init__(self, fields, result):
        self._fields = fields
        self._result = result

    def __getattr__(self, field):
        if field in self._fields:
            value = None
            if field in self._result:
                value = self._result[field][0]
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


class ESQuerySet:
    """
    Provides a Django-like way of querying documents.
    """
    def __init__(self, articlesets: QuerySet, seed=None):
        """
        @param articlesets: articlesets to consider articles from
        @param seed: seed used for random ordering
        """
        self.articlesets = articlesets.only("id")
        self.used_properties = ALL_FIELDS | frozenset(get_used_properties_by_articlesets(self.articlesets))
        self.filters = ()
        self.ordering = ()
        self.seed = seed
        self.fields = ("id", "title", "date")
        self.query_raw = None  # type: Optional[str]
        self.query_term = None  # type: Optional[Term]
        self.highlight = ()
        self.track_scores = False

    def _do_query(self):
        return ES().search(self.get_query())

    @functools.lru_cache()
    def _get_hits(self):
        return self._do_query()["hits"]["hits"]

    def __iter__(self) -> Iterable[ESArticle]:
        hits = self._get_hits()

        if self.highlight:
            for hit in hits:
                yield HighlightedESArticle(self.fields, ChainMap(hit["highlight"], hit["fields"]))
        else:
            for hit in hits:
                yield ESArticle(self.fields, hit["fields"])

    def __len__(self):
        # TODO: Query eleastic for article count
        return len(self._get_hits())

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
            self.seed = random_alphanum(20)
        return self.seed

    def set_seed(self, seed: Optional[str]):
        self.seed = seed

    def get_query(self) -> dict:
        """Return elasticsearch query"""
        aset_ids = [aset.id for aset in self.articlesets]

        query = {
            "track_scores": True if "?" in self.ordering else self.track_scores,
            "fields": self.fields,
            "query": {
                # Using filtered allows us to combine a filter context (boolean query) with
                # a query context (allowing highlighting and scoring)
                "filtered": {
                    "filter": [
                        get_filter_clause("sets", "in", aset_ids)
                    ]
                }
            },
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {}
            },
            "sort": [
                "_doc"
            ]
        }

        # Filters do not calculate scores. On filter is always present (due to filtering
        # on articlesets), so we can safely extend the list even if the user specified
        # no filters
        query["query"]["filtered"]["filter"].extend(self.filters)

        # Highlighting is a bit tricky: the query needs to filter on *all* available fields
        # on the document, but the highlighter can only work on specific fields. We therefore
        # specify the query as a filter and the highlighter on specific fields
        if self.highlight:
            query["query"]["filtered"]["filter"].append(self.query_term.get_dsl())
            query["query"]["filtered"]["query"] = {"bool": {"should": []}}

            for field in self.highlight:
                term_dsl = self.query_term.get_dsl()
                term_dsl["match"][field] = term_dsl["match"].pop("_all")
                query["query"]["filtered"]["query"]["bool"]["should"].append(term_dsl)
                query["highlight"]["fields"][field] = {"no_match_size": 100}

        elif self.query_term:
            query["query"]["filtered"]["query"] = self.query_term.get_dsl()

        # Sorting
        for dir, field in reversed(self.ordering):
            query["sort"].append({field: dir})

        return query

    def only(self, *fields) -> "ESQuerySet":
        self._check_fields(fields)
        return self._copy(fields=fields)

    def query(self, query: str, highlight=(), track_scores=False) -> "ESQuerySet":
        """
        Use a query string to query the final result. Based on this highlights can be made
        and scores can be calculated. If you just want to filter, use filter_query().
        """
        self._check_fields(highlight)
        fields = self.fields
        for field in highlight:
            if field not in fields:
                fields += (field,)
        self.highlight = highlight
        self.track_scores = track_scores
        query_term = queryparser.parse_to_terms(query)
        return self._copy(query_term=query_term, query_raw=query, fields=fields)

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
                field, qualifier = field.rsplit("__", 1)
            self._check_fields((field,))
            new_filters.append(get_filter_clause(field, qualifier, value))

        # Copy self and install new filters
        return self._copy(filters=self.filters + tuple(new_filters))

    def order_by(self, *fields) -> "ESQuerySet":
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

        """
        if fields == (None,):
            return self._copy(fields=())

        # Check for validity
        ordering = []
        for field in fields:
            if field == "?":
                # Random ordering
                raise NotImplementedError("Random ordering not yet supported")
                ordering.append("?")

            order = "asc"
            _field = field
            if field.startswith(("+", "-")):
                if field[0] == "-":
                    order = "desc"
                _field = field[1:]

            if get_property_primitive_type(_field) == str:
                raise NotImplementedError("Ordering on string type not yet supported")

            self._check_fields((_field,))
            ordering.append((order, _field))

        # Copy self and return new one
        return self._copy(ordering=tuple(ordering))

    def _copy(self, **kwargs):
        new = ESQuerySet(ArticleSet.objects.none())
        new.used_properties = self.used_properties
        new.articlesets = self.articlesets
        new.ordering = self.ordering
        new.filters = self.filters
        new.query_term = self.query_term
        new.query_raw = self.query_raw
        new.fields = self.fields
        new.seed = self.seed
        new.highlight = self.highlight
        new.track_scores = self.track_scores

        for attr, value in kwargs.items():
            setattr(new, attr, value)

        return new

    @classmethod
    def from_project(cls, project: Project, **kwargs):
        return cls(project.all_articlesets(), **kwargs)
