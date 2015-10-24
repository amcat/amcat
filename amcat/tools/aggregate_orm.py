"""
Contains logic to aggregate using Postgres / Django ORM, similar to amcates.py.
"""
from collections import defaultdict, OrderedDict
from multiprocessing.pool import ThreadPool
from operator import itemgetter
import logging
import uuid
import itertools
from decimal import Decimal

from django.db import connection

from amcat.models import Article, Medium, CodingJob, ArticleSet
from amcat.models import Code, Coding, CodingValue, CodedArticle, CodingSchemaField
from amcat.models.coding.codingschemafield import  FIELDTYPE_IDS

log = logging.getLogger(__name__)

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

INNER_JOIN = r'INNER JOIN {table} AS T{{prefix}}_{table} ON ({prefix}{t1}.{f1} = T{{prefix}}_{table}.{f2})'


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

    codingjobs = INNER_JOIN.format(
        table=CodingJob._meta.db_table,
        t1=CodedArticle._meta.db_table,
        f1="codingjob_id",
        f2="codingjob_id",
        prefix="T_"
    )

    terms = INNER_JOIN.format(
        table="{{table}}",
        t1=Article._meta.db_table,
        f1="article_id",
        f2="article_id",
        prefix="T_"
    )

DATE_TRUNC_SQL = 'date_trunc(\'{interval}\', "T_articles"."date")'

def merge_aggregations(results):
    results = [{tuple(row[:-1]): row[-1] for row in aggr} for aggr in results]
    keys = set(itertools.chain.from_iterable(aggr.keys() for aggr in results))
    return [list(key) + list(a.get(key) for a in results) for key in keys]


class SQLObject(object):
    joins_needed = []

    def __init__(self, prefix=None):
        self.prefix = uuid.uuid4().hex if prefix is None else prefix

    def get_setup_statements(self):
        """Yield sql statements which should be executed before the aggregation
        begins. This could be used to create and populate temporary tables and
        indices."""
        return ()

    def get_teardown_statements(self):
        """Same as setup_statements, but executed after aggregation."""
        return ()

    def get_selects(self):
        raise NotImplementedError("Subclasses should implement get_selects().")

    def get_joins(self):
        return ()

    def get_wheres(self):
        return ()

    def get_group_by(self):
        return None

class Category(SQLObject):
    def aggregate(self, categories, value, rows):
        """
        Categories may aggregate rows further as they see fit. This can for example
        be used to implement codebook code aggregations.
        """
        return rows

    def get_objects(self, ids):
        return None

    def get_object(self, objects, id):
        return id

    def get_group_by(self):
        return next(iter(self.get_selects()))

class ModelCategory(Category):
    model = None

    def get_objects(self, ids):
        return self.model.objects.in_bulk(ids)

    def get_object(self, objects, id):
        return objects[id]


class IntervalCategory(Category):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, interval, **kwargs):
        super(IntervalCategory, self).__init__(**kwargs)

        if interval not in POSTGRES_DATE_TRUNC_VALUES:
            err_msg = "{} not a valid interval. Choose on of: {}"
            raise ValueError(err_msg.format(interval, POSTGRES_DATE_TRUNC_VALUES))

        self.interval = interval

    def get_selects(self):
        return [DATE_TRUNC_SQL.format(interval=self.interval)]

    def __repr__(self):
        return "<Interval: %s>" % self.interval

class MediumCategory(ModelCategory):
    model = Medium
    joins_needed = ("codings", "coded_articles", "articles")

    def get_selects(self):
        yield 'T_articles.medium_id'

class ArticleSetCategory(ModelCategory):
    model = ArticleSet
    joins_needed = ("codings", "coded_articles", "codingjobs")

    def get_selects(self):
        yield "T_codingjobs.articleset_id"

class TermCategory(Category):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, terms=None, **kwargs):
        # Force random prefix
        super(TermCategory, self).__init__(prefix=None)
        self.terms = terms

    def _get_values(self):
        for term, article_ids in enumerate(self.terms.values()):
            for article_id in article_ids:
                yield article_id, term

    def get_setup_statements(self):
        # Create table
        sql = "CREATE TEMPORARY TABLE T_{prefix}_terms (article_id int, term int);"
        yield sql.format(prefix=self.prefix)

        values = tuple(self._get_values())
        if values:
            sql = "INSERT INTO T_{prefix}_terms (article_id, term) VALUES {values};"
            yield sql.format(prefix=self.prefix, values=str(values)[1:-1])

        # Create index
        sql = "CREATE INDEX T_{prefix}_article_id_index ON T_{prefix}_terms (article_id);"
        yield sql.format(prefix=self.prefix)

        # Analyse table
        yield "ANALYSE T_{prefix}_terms;".format(prefix=self.prefix)

    def get_teardown_statements(self):
        yield "DROP INDEX IF EXISTS T_{prefix}_article_id_index;".format(prefix=self.prefix)
        yield "DROP TABLE IF EXISTS T_{prefix}_terms;".format(prefix=self.prefix)

    def get_joins(self):
        yield JOINS.terms.format(prefix="").format(table="T_{prefix}_terms".format(prefix=self.prefix))

    def get_selects(self):
        yield 'T_T_{prefix}_terms.term'.format(prefix=self.prefix)

    def get_objects(self, ids):
        assert isinstance(self.terms, OrderedDict)
        return dict(enumerate(self.terms.keys()))

    def get_object(self, objects, id):
        return objects.get(id)

    def copy(self, terms):
        return self.__class__(terms)

class SchemafieldCategory(ModelCategory):
    model = Code

    def __init__(self, field, codebook=None, **kwargs):
        super(SchemafieldCategory, self).__init__(**kwargs)
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
        return ['codings_values.intval']

    def get_wheres(self):
        where_sql = 'codings_values.field_id = {field.id}'
        yield where_sql.format(field=self.field)

    def __repr__(self):
        return "<SchemafieldCategory: %s>" % self.field

class Value(SQLObject):
    def __init__(self, **kwargs):
        super(Value, self).__init__(**kwargs)

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

class AverageValue(Value):
    joins_needed = ("codings",)

    def __init__(self, field, *args, **kwargs):
        """@type field: CodingSchemaField"""
        super(AverageValue, self).__init__(*args, **kwargs)
        assert_msg = "Average only aggregates on codingschemafields for now"
        assert isinstance(field, CodingSchemaField), assert_msg
        self.field = field

    def get_joins(self):
        yield JOINS.codings_values.format(prefix=self.prefix)

    def get_wheres(self):
        where_sql = 'T{prefix}_codings_values.field_id = {field_id}'
        yield where_sql.format(field_id=self.field.id, prefix=self.prefix)

    def get_selects(self):
        sql = '{{method}}(T{prefix}_codings_values.intval)'.format(prefix=self.prefix)

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
        return "<AverageValue: %s>" % self.field

class CountValue(Value):
    def postprocess(self, value):
        return int(value[0])

    def aggregate(self, values):
        return [sum(map(itemgetter(0), values))]

class CountArticlesValue(CountValue):
    joins_needed = ("codings", "coded_articles", "articles")

    def get_selects(self):
        return ['COUNT(DISTINCT(T_articles.article_id))']

class CountCodingsValue(CountValue):
    joins_needed = ("codings",)

    def get_selects(self):
        return ['COUNT(DISTINCT(T_coded_articles.id))']

class CountCodingValuesValue(CountValue):
    def get_selects(self):
        return ['COUNT(codings_values.codingvalue_id)']


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
        sql = 'SELECT {selects} FROM "codings_values" {joins} WHERE {wheres}'
        if categories:
            sql += " GROUP BY {groups};"
        else:
            sql += ";"

        # Instantiate TermCategory with terms (HACK)
        for i, category in enumerate(categories):
            if isinstance(category, TermCategory):
                categories[i] = category.copy(self.terms)

        # Add global codings filter
        codings_ids = tuple(self.codings.values_list("id", flat=True))
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

        for setup_statement in setups:
            yield False, setup_statement

        # Build sql statement
        yield True, sql.format(
            selects=",".join(filter(None, selects)),
            joins=" ".join(filter(None, joins)),
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

        return aggregation

