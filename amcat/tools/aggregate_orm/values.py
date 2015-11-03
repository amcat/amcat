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
from amcat.models import CodingSchemaField, FIELDTYPE_IDS
from amcat.tools.aggregate_orm.sqlobj import SQLObject, JOINS


__all__ = (
    "AverageValue",
    "CountValue",
    "CountArticlesValue",
    "CountCodingsValue",
    "CountCodingValuesValue"
)

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