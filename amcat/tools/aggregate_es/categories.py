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

import logging
import datetime
import re

from collections import OrderedDict

import iso8601

from amcat.models import ArticleSet
from amcat.tools import amcates

__all__ = (
    "Category",
    "IntervalCategory",
    "ArticlesetCategory",
    "TermCategory",
    "FieldCategory",
    "IntegerFieldCategory",
    "NumFieldCategory",
    "StringFieldCategory"
)

log = logging.getLogger(__name__)

ELASTIC_TIME_UNITS = [
    "second",
    "minute",
    "hour",
    "day",
    "week",
    "month",
    "quarter",
    "year",
]


class Category(object):
    field = None

    def get_objects(self, ids):
        return ids

    def get_object(self, objects, id):
        return id

    def postprocess(self, value):
        return value

    def get_aggregation(self):
        return {
            self.field: {
                "terms": {
                    "size": 999999,
                    "field": self.field
                }
            }
        }

    def parse_aggregation_result(self, result):
        for bucket in result[self.field]["buckets"]:
            yield bucket["key"], bucket

    def get_column_names(self):
        """Returns names of columns when serializing to a flat format (csv)."""
        raise NotImplementedError("get_column_names() should be implemented by subclasses.")

    def get_column_values(self, obj):
        """Returns values for each column yielded by get_column_names() for an instance."""
        raise NotImplementedError("get_column_values() should be implemented by subclasses.")


class FieldCategory(Category):
    def __init__(self, field):
        self.field = field

        if self.__class__ == FieldCategory:
            raise ValueError("Use FieldCategory.from_fieldname() to instantiate FieldCategory.")

    def get_column_names(self):
        yield self.field

    def get_column_values(self, obj):
        yield obj

    @classmethod
    def from_fieldname(cls, fieldname):
        """Instantiate the correct type of FieldCategory for a given field."""
        ptype = amcates.get_property_primitive_type(fieldname)
        if ptype == datetime.datetime:
            raise ValueError("Use DateFieldCategory() instead of FieldCategroy.from_fieldname for field: {}".format(fieldname))
        elif ptype == int:
            return IntegerFieldCategory(fieldname)
        elif ptype == float:
            return NumFieldCategory(fieldname)
        elif ptype == str:
            return StringFieldCategory(fieldname)
        else:
            raise ValueError("Did not recognize type {} of field {}.".format(ptype, fieldname))


class NumFieldCategory(FieldCategory):
    def postprocess(self, value):
        return float(value)


class IntegerFieldCategory(FieldCategory):
    def postprocess(self, value):
        return int(value)


class StringFieldCategory(FieldCategory):
    def get_aggregation(self):
        aggregation = super(FieldCategory, self).get_aggregation()
        aggregation[self.field]["terms"]["field"] += ".raw"
        return aggregation


class ModelCategory(Category):
    model = None

    def postprocess(self, value):
        return int(value)

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


class ArticlesetCategory(ModelCategory):
    model = ArticleSet
    field = "sets"

    def __init__(self, all_articlesets=None):
        super(ArticlesetCategory, self).__init__()
        if all_articlesets is None:
            log.warning("ArticlesetCategory might return unexpected results if it is not passed the articleset parameter: http://coderify.com/aggregates-array-field-and-autocomplete-funcionality-in-elasticsearch/")
            all_articlesets = ArticleSet.objects.all()
        self.all_articleset_ids = set(all_articlesets.values_list("id", flat=True))

    def parse_aggregation_result(self, result):
        for aset_id, sub in super(ArticlesetCategory, self).parse_aggregation_result(result):
            if aset_id in self.all_articleset_ids:
                yield aset_id, sub

    def __repr__(self):
        return "<ArticlesetCategory>"



class TermCategory(Category):
    def __init__(self, terms):
        self.terms = OrderedDict({t.label: t for t in terms})

    def get_objects(self, ids):
        return self.terms

    def get_object(self, objects, id):
        return objects[id]

    @property
    def bodies(self):
        from amcat.tools.amcates import build_body
        return (dict(build_body(t.query)) for t in self.terms.values())

    def get_aggregation(self):
        for label, body in zip(self.terms.keys(), self.bodies):
            yield label, {"filter": body}

    def parse_aggregation_result(self, result):
        for label in self.terms:
            yield label, result[label]

    def get_column_names(self):
        return self.terms.keys()

    def __repr__(self):
        return "<TermCategory: {}>".format(self.terms)


class IntervalCategory(Category):
    def __init__(self, interval, field="date", fill_zeros=True):
        if interval not in ELASTIC_TIME_UNITS:
            err_msg = "{} not a valid interval. Choose on of: {}"
            raise ValueError(err_msg.format(interval, ELASTIC_TIME_UNITS))
        self.interval = interval
        self.field = field
        self.fill_zeros = fill_zeros

        self.serialize = getattr(self, "_serialize_{}".format(interval), self._serialize_default)
        self.deserialize = getattr(self, "_deserialize_{}".format(interval), self._deserialize_default)

    def _deserialize_default(self, stamp: str) -> datetime.datetime:
        return iso8601.iso8601.parse_date(stamp, default_timezone=None)

    def _deserialize_year(self, stamp: str) -> datetime.datetime:
        return datetime.datetime(int(stamp), 1, 1)

    def _deserialize_quarter(self, stamp: str):
        year, quarter = map(int, stamp.split("-Q"))
        return datetime.datetime(year, (quarter - 1) * 3 + 1, 1)

    def _deserialize_month(self, stamp: str):
        return self._deserialize_default(stamp + "-1")

    def _deserialize_week(self, stamp: str):
        return datetime.datetime.strptime(stamp + '-0', "%Y-%W-%w")

    def _serialize_default(self, stamp: datetime.datetime) -> str:
        return stamp.isoformat()

    def _serialize_year(self, stamp: datetime.datetime) -> str:
        return str(stamp.year)

    def _serialize_quarter(self, stamp: datetime.datetime):
        quarter = ((stamp.month - 1) // 3) + 1
        return "{}-Q{}".format(stamp.year, quarter)

    def _serialize_month(self, stamp: datetime.datetime) -> str:
        return stamp.strftime("%Y-%m")

    def _serialize_week(self, stamp: datetime.datetime) -> str:
        return stamp.strftime("%Y-%W")

    def _serialize_day(self, stamp: datetime.datetime) -> str:
        return stamp.date().isoformat()

    def postprocess(self, value) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(value / 1000)

    def get_object(self, _, timestamp: datetime.datetime):
        return self.serialize(timestamp)

    def get_aggregation(self):
        return {
            "date": {
                "date_histogram": {
                    "field": "date",
                    "interval": self.interval,
                    "min_doc_count": 0 if self.fill_zeros else 1
                }
            }
        }

    def get_column_names(self):
        yield "date"

    def get_column_values(self, obj):
        yield obj

    def __repr__(self):
        return "<IntervalCategory: {} per {}>".format(self.field, self.interval)
