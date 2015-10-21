"""
Contains logic to aggregate using Postgres / Django ORM, similar to amcates.py.
"""
from collections import defaultdict
from multiprocessing.pool import ThreadPool
from operator import itemgetter
import uuid
import itertools
from decimal import Decimal

from django.db import connection

from amcat.models import Article, Medium
from amcat.models import Code, Coding, CodingValue, CodedArticle, CodingSchemaField
from amcat.models.coding.codingschemafield import  FIELDTYPE_IDS

POSTGRES_DATE_TRUNC_VALUES = [
    "microseconds",
    "milliseconds",
    "second",
    "minute",
    "hour",
    "day",
    "week",
    "month",
    "quarter",
    "year",
    "decade",
    "century",
    "millennium"
]

INNER_JOIN = r'INNER JOIN "{table}" AS "T{{prefix}}_{table}" ON ("{prefix}{t1}"."{f1}" = "T{{prefix}}_{table}"."{f2}")'


class JOINS:
    codings = INNER_JOIN.format(
        table=Coding._meta.db_table, 
        t1=CodingValue._meta.db_table, 
        f1="coding_id", 
        f2="coding_id",
        prefix=""
    )

    coded_articles = INNER_JOIN.format(
        table=CodedArticle._meta.db_table,
        t1=Coding._meta.db_table, 
        f1="coded_article_id",
        f2="id",
        prefix="T_"
    )
    
    articles = INNER_JOIN.format(
        table=Article._meta.db_table, 
        t1=CodedArticle._meta.db_table,
        f1="article_id", 
        f2="article_id",
        prefix="T_"
    )

    codings_values = INNER_JOIN.format(
        table=CodingValue._meta.db_table,
        t1=Coding._meta.db_table, 
        f1="coding_id", 
        f2="coding_id",
        prefix="T_"
    )

DEFAULT_JOINS = (
    JOINS.codings.format(prefix=""),
    JOINS.coded_articles.format(prefix=""),
    JOINS.articles.format(prefix="")
)

DATE_TRUNC_SQL = 'date_trunc(\'{interval}\', "T_articles"."date")'

def merge_aggregations(results):
    results = [{tuple(row[:-1]): row[-1] for row in aggr} for aggr in results]
    keys = set(itertools.chain.from_iterable(aggr.keys() for aggr in results))
    return [list(key) + list(a.get(key) for a in results) for key in keys]


class SQLObject(object):
    def get_selects(self):
        raise NotImplementedError("Subclasses should implement get_selects().")

    def get_joins(self):
        return ()

    def get_wheres(self):
        return ()

    def get_group_by(self):
        return None

class Category(SQLObject):
    model = None

    def aggregate(self, categories, value, rows):
        """
        Categories may aggregate rows further as they see fit. This can for example
        be used to implement codebook code aggregations.
        """
        return rows

    def get_group_by(self):
        return next(iter(self.get_selects()))

class IntervalCategory(Category):
    def __init__(self, interval):
        super(IntervalCategory, self).__init__()

        if interval not in POSTGRES_DATE_TRUNC_VALUES:
            err_msg = "{} not a valid interval. Choose on of: {}"
            raise ValueError(err_msg.format(interval, POSTGRES_DATE_TRUNC_VALUES))

        self.interval = interval

    def get_selects(self):
        return [DATE_TRUNC_SQL.format(interval=self.interval)]

    def __repr__(self):
        return "<Interval: %s>" % self.interval

class MediumCategory(Category):
    model = Medium

    def get_selects(self):
        return ['"T_articles"."medium_id"']

class SchemafieldCategory(Category):
    model = Code

    def __init__(self, field, codebook=None):
        super(SchemafieldCategory, self).__init__()
        self.field = field
        self.codebook = codebook
        self.aggregation_map = {}

        if self.codebook is not None:
            self.codebook.cache()
            for root_node in self.codebook.get_tree():
                self.aggregation_map[root_node.code_id] = root_node.code_id
                for descendant in root_node.get_descendants():
                    self.aggregation_map[descendant.code_id] = root_node.code_id

    def _aggregate(self, categories, value, rows):
        num_categories = len(categories)
        self_index = categories.index(self)

        # First do a sanity check. If a coding specifies a code which is
        # NOT present in the given codebook, raise an error.
        coded_codes = set(map(itemgetter(self_index), rows))
        codebook_codes = set(self.codebook.get_code_ids())
        invalid_codes = coded_codes - codebook_codes

        if invalid_codes:
            error_message = "Codes with ids {} were used in {}, but are not present in {}."
            raise ValueError(error_message.format(invalid_codes, self.field, self.codebook))

        # Create a mapping from key -> rownrs which need to be aggregated
        to_aggregate = defaultdict(list)
        for n, row in enumerate(rows):
            key = row[:self_index] + [self.aggregation_map[row[self_index]]] + row[self_index+1:num_categories]
            to_aggregate[tuple(key)].append(n)

        for key, rownrs in to_aggregate.items():
            values = [row[num_categories:] for row in [rows[rownr] for rownr in rownrs]]
            yield list(key) + value.aggregate(values)

    def aggregate(self, categories, value, rows):
        if self.codebook is None:
            return super(SchemafieldCategory, self).aggregate(categories, value, rows)
        return self._aggregate(categories, value, rows)

    def get_selects(self):
        return ['"codings_values"."intval"']

    def get_wheres(self):
        where_sql = '"codings_values"."field_id" = {field.id}'
        yield where_sql.format(field=self.field)

    def __repr__(self):
        return "<SchemafieldCategory: %s>" % self.field

class BaseAggregationValue(SQLObject):
    def __init__(self, prefix=None):
        super(BaseAggregationValue, self).__init__()
        self.prefix = uuid.uuid4().hex if prefix is None else prefix

    def aggregate(self, values):
        """
        Categories may request further aggregation in Python code, Each subclass
        will need to implement a proper way to deal with this. For example, you can
        simply add counts, but for averages you would need a weight too.
        """
        raise NotImplementedError("Subclasses should implement aggregate()")

    def postprocess(self, value):
        """
        Last step after all aggregation steps are done. Convert the (multiple)
        selects into a single value.
        """
        return value

class Average(BaseAggregationValue):
    def __init__(self, field, *args, **kwargs):
        """@type field: CodingSchemaField"""
        super(Average, self).__init__(*args, **kwargs)
        assert_msg = "Average only aggregates on codingschemafields for now"
        assert isinstance(field, CodingSchemaField), assert_msg
        self.field = field

    def get_joins(self):
        yield JOINS.codings_values.format(prefix=self.prefix)

    def get_wheres(self):
        where_sql = '"T{prefix}_codings_values"."field_id" = {field_id}'
        yield where_sql.format(field_id=self.field.id, prefix=self.prefix)

    def get_selects(self):
        sql = '{{method}}("T{prefix}_codings_values"."intval")'.format(prefix=self.prefix)

        # Yield weight select
        yield sql.format(method="COUNT")

        # Yield AVERAGE select
        avg_sql = sql.format(method="AVG")
        if self.field.fieldtype_id == FIELDTYPE_IDS.QUALITY:
            avg_sql += "/10.0"
        yield avg_sql

    def aggregate(self, values):
        # Quick check to prevent lots of calculations if not necessary
        if len(values) == 1:
            weight, value = values[0]
            return [1, value]

        average = Decimal(0)
        for weight, value in values:
            average += weight * value

        total_weight = sum(map(itemgetter(0), values))
        return [total_weight, average / total_weight]

    def postprocess(self, value):
        weight, value = value
        return float(value)

    def __repr__(self):
        return "<Average: %s>" % self.field

class Count(BaseAggregationValue):
    def get_selects(self):
        return ['COUNT(DISTINCT("T_articles"."article_id"))']

    def postprocess(self, value):
        return int(value[0])

    def aggregate(self, values):
        return [sum(map(itemgetter(0), values))]


class ORMAggregate(object):
    def __init__(self, codings, flat=False, threaded=True):
        """
        @type codings: QuerySet
        """
        self.codings = codings
        self.flat = flat
        self.threaded = threaded

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
        sql = 'SELECT {selects} FROM "codings_values" {joins} WHERE {wheres}'
        if categories:
            sql += " GROUP BY {groups}"
        sql += ';'

        codings_ids = tuple(self.codings.values_list("id", flat=True))
        wheres = ['"codings_values"."coding_id" IN {}'.format(codings_ids)]

        # Gather all separate sql statements
        selects, joins, groups = [], list(DEFAULT_JOINS), []
        for sqlobj in itertools.chain(categories, [value]):
            groups.append(sqlobj.get_group_by())
            selects.extend(sqlobj.get_selects())
            joins.extend(sqlobj.get_joins())
            wheres.extend(sqlobj.get_wheres())

        # Build sql statement
        return sql.format(
            selects=",".join(filter(None, selects)),
            joins=" ".join(filter(None, joins)),
            wheres="({})".format(") AND (".join(filter(None, wheres))),
            groups=",".join(filter(None, groups))
        )

    def _execute_sql(self, query):
        with connection.cursor() as c:
            c.execute(query)
            return list(map(list, c.fetchall()))

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
        queries = [self._get_aggregate_sql(categories, value) for value in values]

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
            if category.model is None:
                continue
            pks = [row[i] for row in aggregation]
            objs = category.model.objects.in_bulk(pks)
            for row in aggregation:
                row[i] = objs[row[i]]

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

        return aggregation

