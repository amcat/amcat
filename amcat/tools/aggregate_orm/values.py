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
from decimal import Decimal
from operator import itemgetter
from amcat.models import CodingSchemaField, FIELDTYPE_IDS, Coding, CodedArticle, CodingValue
from amcat.tools.aggregate_orm.sqlobj import SQLObject, JOINS
from amcat.tools.aggregate_orm.categories import SchemafieldCategory

__all__ = (
    "Value",
    "AverageValue",
    "CountValue",
    "CountArticlesValue",
    "CountCodingsValue",
    "CountCodingValuesValue",
    "CountSelectedCodingsValue"
)


class Value(SQLObject):
    def __init__(self, **kwargs):
        super(Value, self).__init__(**kwargs)
        self._first_field_hack = None

    def _set_first_field_aggregation(self, field):
        """HACK: the caller may set the last field aggregation (SchemafieldCategory). This is
        currently used in AverageValue, to determine which JOINS are needed. For example, a user
        might aggregate on an article schema, and still expect sentence field value aggregations
        to work (which would be included due to the first aggregation). In other words; and extra
        join is needed. On the other hand, aggregating on a sentence field AND aggregating on a
        sentence value should not yield the same join.
        """
        self._first_field_hack = field

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

    def get_column_names(self):
        yield "Value"

    def get_column_values(self, obj):
        yield obj


class AverageValue(Value):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, field, *args, **kwargs):
        """@type field: CodingSchemaField"""
        super(AverageValue, self).__init__(*args, **kwargs)
        assert_msg = "Average only aggregates on codingschemafields for now"
        assert isinstance(field, CodingSchemaField), assert_msg
        self.field = field

    @property
    def need_extra_joins(self):
        if self._first_field_hack is None:
            return False
        field_schema = self.field.codingschema
        last_field_schema = self._first_field_hack.field.codingschema
        return field_schema.isarticleschema is not last_field_schema.isarticleschema

    def get_joins(self, seen_categories=None):
        prefix = "{}_2".format(self.prefix)

        if self.need_extra_joins:
            # codings -> coded_article -> codings -> coding_values
            yield JOINS.coded_articles.format(prefix=self.prefix)
            yield "INNER JOIN {} AS {} ON ({} = {})".format(
                Coding._meta.db_table,
                "T{}_{}".format(prefix, Coding._meta.db_table),
                "T{}_{}.id".format(self.prefix, CodedArticle._meta.db_table),
                "T{}_{}.coded_article_id".format(prefix, Coding._meta.db_table),
            )
            yield "INNER JOIN {} AS {} ON ({} = {})".format(
                CodingValue._meta.db_table,
                "T{}_{}".format(prefix, CodingValue._meta.db_table),
                "T{}_{}.coding_id".format(prefix, Coding._meta.db_table),
                "T{}_{}.coding_id".format(prefix, CodingValue._meta.db_table),
            )

        yield JOINS.codings_values.format(prefix=self.prefix)

    def get_wheres(self):
        prefix = "{}_2".format(self.prefix) if self.need_extra_joins else self.prefix
        where_sql = 'T{prefix}_codings_values.field_id = {field_id}'
        yield where_sql.format(field_id=self.field.id, prefix=prefix)

        if self.need_extra_joins:
            if self.field.codingschema.isarticleschema:
                yield "T{}_{}.sentence_id IS NULL".format(prefix, Coding._meta.db_table)
            else:
                yield "T{}_{}.sentence_id IS NOT NULL".format(prefix, Coding._meta.db_table)

    def get_selects(self, seen_categories=None):
        prefix = "{}_2".format(self.prefix) if self.need_extra_joins else self.prefix
        sql = '{{method}}(T{prefix}_codings_values.intval)'.format(prefix=prefix)

        # Yield weight select
        yield sql.format(method="COUNT")

        # Yield AVERAGE select
        avg_sql = sql.format(method="AVG")
        if self.field.fieldtype_id == FIELDTYPE_IDS.QUALITY:
            avg_sql += "/10.0"
        yield avg_sql
        yield 'ARRAY_AGG(DISTINCT(T_articles.article_id) ORDER BY T_articles.article_id)'

    def aggregate(self, values):
        # Quick check to prevent lots of calculations if not necessary
        if len(values) == 1:
            weight, value, ids = values[0]
            return [1, value, ids]

        average = Decimal(0)
        ids = []
        for weight, value, article_ids in values:
            average += weight * value
            ids.extend(article_ids)

        total_weight = sum(map(itemgetter(0), values))
        return [total_weight, average / total_weight, ids]

    def postprocess(self, value):
        weight, value, ids = value
        return float(value), tuple(ids)

    def get_column_names(self):
        return "Average {}".format(self.field.label),

    def get_column_values(self, obj):
        yield obj[0]

    def __repr__(self):
        return "<AverageValue: %s>" % self.field


class CountValue(Value):
    _art_ids_agg = 'ARRAY_AGG(DISTINCT(T_articles.article_id) ORDER BY T_articles.article_id)'

    def postprocess(self, value):
        return (int(value[0]), tuple(value[1]))

    def aggregate(self, values):
        return [sum(map(itemgetter(0), values))] + [v[1] for v in values]

    def get_column_values(self, obj):
        yield obj if isinstance(obj, int) else obj[0]


class CountArticlesValue(CountValue):
    joins_needed = ("codings", "coded_articles", "articles")

    def get_selects(self, seen_categories=None):
        return ['COUNT(DISTINCT(T_articles.article_id))', self._art_ids_agg]

    def get_column_names(self):
        return "Article Count",

    def __repr__(self):
        return "<CountArticlesValue>"


class CountCodingsValue(CountValue):
    joins_needed = ("codings", "coded_articles", "articles")

    def get_selects(self, seen_categories=None):
        codings_table = "T_codings"
        # IF one of the aggregations is on a coding, use that table instead
        if seen_categories:
            schemacats = {c.isarticleschemafield: c for c in seen_categories if isinstance(c, SchemafieldCategory)}
            if False in schemacats: # prefer a unit schema field
                codings_table = schemacats[False].codings_table
            elif True in schemacats: # otherwise, try an article schema field
                codings_table = schemacats[True].codings_table

        return ['COUNT(DISTINCT({codings_table}.coding_id))'.format(codings_table=codings_table),
                self._art_ids_agg]

    def get_column_names(self):
        return "Distinct Codings",

    def get_wheres(self):
        yield "T_codings.sentence_id IS NOT NULL"

    def __repr__(self):
        return "<CountCodingsValue>"


class CountSelectedCodingsValue(CountCodingsValue):
    joins_needed = ("codings", "coded_articles", "articles")

    def __init__(self, filters, use_or=False, **kwargs):
        super().__init__(**kwargs)
        self.filters = filters
        self.use_or = use_or

    def get_wheres(self):
        yield from super().get_wheres()
        in_conditions = (
            "("
            "SELECT {T}.coding_id "
            "FROM codings_values as {T} "
            "WHERE {T}.field_id = {field_id} "
            "AND {T}.intval IN ({intvals}) "
            ")".format(
                T="T{}_{}_codings_values_inner".format(self.prefix, i),
                intvals=",".join(str(int(id)) for id in code_ids),
                field_id=field.id
            )
            for i, (field, code_ids) in enumerate(self.filters)
            if not field.codingschema.isarticleschema
        )
        if self.use_or:
            return " OR ".join("(T_codings.coding_id IN {})".format(in_condition) for in_condition in in_conditions)

        for in_condition in in_conditions:
            yield "T_codings.coding_id IN {}".format(in_condition)

    def get_column_names(self):
        return "Distinct Selected Codings",

    def __repr__(self):
        return "<CountSelectedCodingsValue>"


class CountCodingValuesValue(CountValue):
    joins_needed = ("codings", "coded_articles", "articles")

    def get_selects(self, seen_categories=None):
        return ['COUNT(DISTINCT(codings_values.codingvalue_id))', self._art_ids_agg]

    def get_column_names(self):
        return "Distinct Coding Values",

    def __repr__(self):
        return "<CountCodingValuesValue>"
