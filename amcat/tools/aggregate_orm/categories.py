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
from amcat.models.coding.codebook import get_tree_levels
from amcat.tools.aggregate_orm.sqlobj import SQLObject, JOINS
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
    "SchemafieldCategory",
    "GroupedCodebookFieldCategory",
)


class Category(SQLObject):

    def __init__(self, *args, is_primary=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_primary = is_primary

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
        return "term", "query"

    def get_column_values(self, obj):
        """@type obj: SearchQuery"""
        return obj.label, obj.query

    def __repr__(self):
        return "<TermCategory: {}>".format(self.terms)


class SchemafieldCategory(ModelCategory):
    model = Code

    def __init__(self, field, coding_ids=None, **kwargs):
        super(SchemafieldCategory, self).__init__(**kwargs)
        self.coding_ids = coding_ids
        self.field = field

    def get_selects(self):
        return ['{T}.intval'.format(T=self.table_name)]

    @property
    def table_name(self):
        if self.is_primary:
            return "codings_values"
        return "T{}_codings_values".format(self.prefix)

    def get_joins(self):
        if self.is_primary:
            return

        yield "INNER JOIN codings as T{prefix}_codings " \
              "ON T{prefix}_codings.coded_article_id = T_coded_articles.id".format(prefix=self.prefix)
        yield "INNER JOIN codings_values as T{prefix}_codings_values " \
              "ON T{prefix}_codings.coding_id = T{prefix}_codings_values.coding_id".format(prefix=self.prefix)

    def get_wheres(self):
        where_sql = '{T}.field_id = {field.id}'
        yield where_sql.format(T=self.table_name, field=self.field)

        if not self.is_primary:
            yield '{T}.coding_id IN (SELECT * from codings_queryset)'.format(T=self.table_name)

        if self.coding_ids is not None:
            yield '{T}.intval IN ({vs})'.format(T=self.table_name, vs=",".join(map(str, self.coding_ids)))

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.field)


class GroupedCodebookFieldCategory(SchemafieldCategory):
    def __init__(self, *args, codebook, level, **kwargs):
        self.codebook = codebook
        self.level = level
        super().__init__(*args, **kwargs)
        self.t_hierarchy = "T_{}_hierarchy".format(self.prefix)

    def get_setup_statements(self):

        # builds a table of (code_id, ancestor_id) for the lowest ancestor at the given level or higher.
        sql = """
            CREATE TEMPORARY TABLE {T} AS 
            (
                WITH RECURSIVE codebook_hierarchy AS (
                     SELECT roots.codebook_id, roots.code_id, ARRAY[roots.code_id] as hierarchy, Array[cd.label] as labels  -- select root elements
                     FROM codebooks_codes roots
                     JOIN codes cd ON cd.code_id = roots.code_id
                         WHERE roots.parent_id ISNULL
                         AND roots.codebook_id = {codebook_id}
                     UNION ALL    -- recursively union with children, building an array of ancestors
                     SELECT child.codebook_id, child.code_id, parent.hierarchy || child.code_id, parent.labels || cd2.label
                     FROM codebooks_codes child
                     JOIN codes cd2 ON cd2.code_id = child.code_id
                     JOIN codebook_hierarchy as parent ON parent.code_id = child.parent_id AND parent.codebook_id = child.codebook_id
                )
                SELECT code_id, hierarchy[least(array_upper(hierarchy, 1), {level})] as root_id, hierarchy, labels FROM codebook_hierarchy
            );
            CREATE INDEX {T}_code_id ON {T} (code_id);
        """
        yield sql.format(codebook_id=int(self.codebook.id), level=int(self.level), T=self.t_hierarchy)

    def get_teardown_statements(self):
        yield "DROP TABLE IF EXISTS {T};".format(T=self.t_hierarchy)

    def get_joins(self):
        yield from super().get_joins()
        yield "JOIN {THierarchy} as T_{THierarchy} " \
              "ON (T_{THierarchy}.code_id = {TValue}.intval)".format(
            THierarchy=self.t_hierarchy,
            TValue=self.table_name)

    def get_selects(self):
        yield "T_{T}.root_id".format(T=self.t_hierarchy)

    def get_order_by(self):
        yield "T_{T}.labels".format(T=self.t_hierarchy)
