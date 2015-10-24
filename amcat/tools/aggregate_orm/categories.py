from collections import OrderedDict, defaultdict
from operator import itemgetter
from amcat.models import Medium, ArticleSet, Code
from amcat.tools.aggregate_orm.sqlobj import SQLObject, JOINS

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

DATE_TRUNC_SQL = 'date_trunc(\'{interval}\', "T_articles"."date")'

__all__ = (
    "IntervalCategory",
    "MediumCategory",
    "ArticleSetCategory",
    "TermCategory",
    "SchemafieldCategory"
)


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