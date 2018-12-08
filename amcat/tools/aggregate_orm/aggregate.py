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
Contains logic to aggregate using Postgres / Django ORM, similar to amcates.py.
"""
import datetime
from collections import OrderedDict
from multiprocessing.pool import ThreadPool
import logging
import itertools

from django.db import connection

from amcat.models import Coding, CodingSchemaField
from amcat.tools.aggregate_orm.categories import TermCategory, SchemafieldCategory
from amcat.tools.aggregate_orm.sqlobj import JOINS

log = logging.getLogger(__name__)

__all__ = ("ORMAggregate",)


def merge_aggregations(results):
    results = [{tuple(row[:-1]): row[-1] for row in aggr} for aggr in results]
    keys = set(itertools.chain.from_iterable(aggr.keys() for aggr in results))
    return [list(key) + list(a.get(key) for a in results) for key in keys]


class ORMAggregate(object):
    def __init__(self, codings, terms=None, flat=False, threaded=True):
        """
        @type codings: QuerySet
        @param terms: mapping of label to list of article ids. This will be used
                      by TermCategory. Ideally, we would instantiate TermCategory
                      with this, but the article ids are often only known at the time
                      of instantiating ORMAggregate.
        """
        self.codings = codings
        self.flat = flat
        self.threaded = threaded
        self.terms = OrderedDict(terms if terms else {})


    @classmethod
    def from_articles(self, article_ids, codingjob_ids, **kwargs):
        """
        @type article_ids: sequence of ints
        @type codingjob_ids: sequence of ints
        """
        codings = Coding.objects.filter(coded_article__article__id__in=article_ids)
        codings = codings.filter(coded_article__codingjob__id__in=codingjob_ids)
        return ORMAggregate(codings, **kwargs)

    def _get_aggregate_sql(self, categories, value):
        # Build SQL template
        sql = 'SELECT {selects}\nFROM "codings_values"\n{joins}\nWHERE {wheres}'
        if categories:
            sql += "\nGROUP BY {groups};"
        else:
            sql += ";"

        # Instantiate TermCategory with terms (HACK)
        for i, category in enumerate(categories):
            if isinstance(category, TermCategory):
                categories[i] = category.copy(self.terms)

        # Add global codings filter
        codings_ids = tuple(self.codings.values_list("id", flat=True)) + (-1,)
        wheres = ['codings_values.coding_id IN {}'.format(codings_ids)]

        # Gather all separate sql statements
        joins_needed = set()
        setups, selects, joins, groups, teardowns = [], [], [], [], []
        for sqlobj in itertools.chain(categories, [value]):
            joins_needed.update(sqlobj.joins_needed)
            setups.extend(sqlobj.get_setup_statements())
            groups.append(sqlobj.get_group_by())
            selects.extend(sqlobj.get_selects())
            joins.extend(sqlobj.get_joins())
            wheres.extend(sqlobj.get_wheres())
            teardowns.extend(sqlobj.get_teardown_statements())

        seen = set()
        for join in reversed(("codings", "coded_articles", "articles", "codingjobs")):
            if join in joins_needed and join not in seen:
                joins.insert(0, getattr(JOINS, join).format(prefix=""))
                seen.add(join)

        setups.insert(0, "CREATE TEMPORARY TABLE codings_queryset AS ("
                         "  SELECT coding_id "
                         "  FROM codings "
                         "  WHERE coding_id IN {}"
                         ")".format(codings_ids))
        teardowns.append('DROP TABLE codings_queryset')

        for setup_statement in setups:
            yield False, setup_statement

        # Build sql statement
        yield True, sql.format(
            selects=",".join(filter(None, selects)),
            joins="\n".join(filter(None, joins)),
            wheres="({})".format(") AND (".join(filter(None, wheres))),
            groups=",".join(filter(None, groups))
        )

        for teardown_statement in teardowns:
            yield False, teardown_statement

    def _execute_sql(self, queries):
        results = []
        with connection.cursor() as c:
            for collect_results, query in queries:
                c.execute(query)
                if collect_results:
                    results.extend(map(list, c.fetchall()))
            return results

    def _execute_sqls(self, queries):
        if not self.threaded:
            return list(map(self._execute_sql, queries))

        # Instantiate threadpool and use it to map over queries
        threadpool = ThreadPool(max(4, len(queries)))
        try:
            return list(threadpool.map(self._execute_sql, queries))
        finally:
            threadpool.close()

    def _get_aggregate(self, categories, values):
        # HACK: Determine last field category. See _set_last_field_aggregation() for info.
        first_field_category = ([c for c in categories if isinstance(c, SchemafieldCategory)] + [None])[0]
        for value in values:
            value._set_first_field_aggregation(first_field_category)

        queries = [list(self._get_aggregate_sql(categories, value)) for value in values]
        aggregations = list(self._execute_sqls(queries))

        # Aggregate further in Python code
        for n, (value, rows) in enumerate(zip(values, aggregations)):
            for category in reversed(categories):
                rows = list(category.aggregate(categories, value, rows))
            aggregations[n] = rows

        # Convert to single value / Python type
        for n, (value, rows) in enumerate(zip(values, aggregations)):
            for row in rows:
                row[len(categories):] = [value.postprocess(row[len(categories):])]

        # Merge aggregations
        aggregation = list(merge_aggregations(aggregations))

        # Replace ids with model objects
        for i, category in enumerate(categories):
            pks = [row[i] for row in aggregation]
            objs = category.get_objects(pks)
            for row in aggregation:
                row[i] = category.get_object(objs, row[i])

        # Flat representation to ([cats], [vals])
        num_categories = len(categories)
        for row in aggregation:
            yield tuple(row[:num_categories]), tuple(row[num_categories:])

    def get_aggregate(self, categories=(), values=(), allow_empty=True):
        """
        @type categories: iterable of Category
        @type values: iterable of Value
        """
        if not self.codings.count():
            return iter([])

        if not values:
            raise ValueError("You must specify at least one value.")

        aggregation = self._get_aggregate(list(categories), list(values))

        # Filter values like (1, None)
        if not allow_empty:
            aggregation = ((cats, vals) for cats, vals in aggregation if all(vals))

        # Flatten categories, i.e. [((Medium,), (1, 2))] to [((Medium, (1, 2))]
        if self.flat and len(categories) == 1:
            aggregation = ((cat[0], vals) for cat, vals in aggregation)

        # Flatten values, i.e. [(Medium, (1,))] to [(Medium, 1)]
        if self.flat and len(values) == 1:
            aggregation = ((cats, val[0]) for cats, val in aggregation)

        # Filter duplicate rows
        return iter(set(aggregation))

