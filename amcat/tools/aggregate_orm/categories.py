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
import logging

from collections import OrderedDict, defaultdict
from operator import itemgetter
from typing import List, Mapping, Tuple
from uuid import uuid4

from amcat.models import ArticleSet, Code, Article
from amcat.tools.aggregate_orm.sqlobj import SQLObject, JOINS, INNER_JOIN
from amcat.tools.amcates import get_property_primitive_type

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

DATE_TRUNC_SQL = 'date_trunc(\'{interval}\', T_articles.{field_name})'
DATE_TRUNC_JSON_SQL = 'date_trunc(\'{interval}\', T_articles.properties->>\'{field_name}\')'

__all__ = (
    "Category",
    "ArticleFieldCategory",
    "IntervalCategory",
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

    def get_column_names(self):
        """Returns names of columns when serializing to a flat format (csv)."""
        raise NotImplementedError("get_column_names() should be implemented by subclasses.")

    def get_column_values(self, obj):
        """Returns values for each column yielded by get_column_names() for an instance."""
        raise NotImplementedError("get_column_values() should be implemented by subclasses.")


class ArticleFieldCategory(Category):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, is_json_field: bool, field_name: str, groupings: Mapping[str, Tuple[str]] = None, **kwargs):
        """
        Initializes the ArticleFieldCategory.
        If groupings are given as a key:values dict, the values in the given list are grouped into the key, and treated
        as one single value. If it is None, no grouping is performed.
        """
        super().__init__(**kwargs)
        self.is_json_field = is_json_field
        self.field_name = field_name

        self.groupings = None
        if groupings:
            self.groupings = groupings
            self.group_prefix = uuid4().hex
            # our temp table
            self._T = "T_{group_prefix}_groups".format(group_prefix=self.group_prefix)
            self.joins_needed += (self._T, )

    def get_setup_statements(self):
        if not self.groupings:
            return

        sql = "CREATE TEMPORARY TABLE {T} (from_field text, to_field text);"
        yield sql.format(T=self._T)
        insert_tuples = []
        for k, others in self.groupings.items():
            for other in others:
                insert_tuples.append((other, k))
        yield "INSERT INTO {T} VALUES {vs};".format(T=self._T, vs=",".join(str(t) for t in insert_tuples))
        yield "CREATE INDEX {T}_from_field_index ON {T} (from_field);" .format(T=self._T)

    def get_teardown_statements(self):
        if not self.groupings:
            return
        yield "DROP INDEX IF EXISTS {T}_from_field_index;".format(T=self._T)
        yield "DROP TABLE IF EXISTS  {T};".format(T=self._T)

    def _get_select(self):
        if self.is_json_field:
            return "T_articles.properties->>\'{}\'".format(self.field_name)
        else:
            return "T_articles.{}".format(self.field_name)

    def get_selects(self):
        if self.groupings:
            yield "coalesce({T}.to_field, {select})".format(T=self._T, select=self._get_select())
        else:
            yield self._get_select()


    def get_joins(self):
        if not self.groupings:
            return
        select = self._get_select()
        yield "LEFT JOIN {T} ON ({T}.from_field = {select})".format(T=self._T, select=select)

    @classmethod
    def from_field_name(cls, field_name: str, **kwargs):
        """Construct a category object corresponding to the field_name's type. For example,
        the field 'date' would map to a IntervalCategory, while author would map to
        TextCategory.

        @param kwargs: additional parameters passed to corresponding Category"""
        is_json_field = field_name not in Article.static_fields()
        field_type = get_property_primitive_type(field_name)

        if field_type in (int, str, float):
            return ArticleFieldCategory(is_json_field=is_json_field, field_name=field_name, **kwargs)
        elif field_type == datetime.datetime:
            return IntervalCategory(is_json_field=is_json_field, field_name=field_name, **kwargs)
        else:
            raise ValueError("Did not recognize primitive field type: {} (on {})".format(field_type, field_name))

    def get_column_names(self):
        yield self.field_name

    def get_column_values(self, obj):
        """@type obj: int, float, str"""
        yield str(obj)


class IntervalCategory(ArticleFieldCategory):

    def __init__(self, interval, field_name="date", **kwargs):
        super().__init__(field_name=field_name, **kwargs)

        if interval not in POSTGRES_DATE_TRUNC_VALUES:
            err_msg = "{} not a valid interval. Choose on of: {}"
            raise ValueError(err_msg.format(interval, POSTGRES_DATE_TRUNC_VALUES))

        self.interval = interval

    def get_selects(self):
        if self.is_json_field:
            return [DATE_TRUNC_JSON_SQL.format(interval=self.interval, field_name=self.field_name)]
        else:
            return [DATE_TRUNC_SQL.format(interval=self.interval, field_name=self.field_name)]

    def get_column_values(self, obj):
        """@type obj: datetime.datetime"""
        yield obj.isoformat()

    def __repr__(self):
        return "<IntervalCategory: %s>" % self.interval


class DuplicateLabelError(ValueError):
    pass


class InvalidReferenceError(ValueError):
    pass


class ModelCategory(Category):
    model = None

    def get_objects(self, ids):
        return self.model.objects.in_bulk(ids)

    def get_object(self, objects, id):
        return objects[id]

    def get_column_names(self):
        model_name = self.model.__name__.lower()
        return model_name + "_id", model_name + "_label"

    def get_column_values(self, obj):
        return obj.id, getattr(obj, obj.__label__)

    def __repr__(self):
        return "<ModelCategory: {}>".format(self.model.__name__)


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

    def get_column_names(self):
        yield "term"

    def get_column_values(self, obj):
        """@type obj: SearchQuery"""
        yield obj.label

    def __repr__(self):
        return "<TermCategory: {}>".format(self.terms)


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
            key = row[:self_index] + [self.aggregation_map[row[self_index]]] + row[self_index + 1:num_categories]
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

