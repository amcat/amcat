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

from collections import OrderedDict

from amcat.models import ArticleSet, Medium

log = logging.getLogger(__name__)

ELASTIC_TIME_UNITS = [
    "milli-second",
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
        expected_fields = 2 if "doc_count" in result else 1
        assert len(result) == expected_fields

        for bucket in result.values()[0]["buckets"]:
            yield bucket["key"], bucket


class ModelCategory(Category):
    model = None

    def postprocess(self, value):
        return int(value)

    def get_objects(self, ids):
        return self.model.objects.in_bulk(ids)

    def get_object(self, objects, id):
        return objects[id]


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


class MediumCategory(ModelCategory):
    model = Medium
    field = "medium"

    def parse_aggregation_result(self, result):
        result = super(MediumCategory, self).parse_aggregation_result(result)
        next(result)
        return result


class TermCategory(Category):
    def __init__(self, terms):
        self.terms = OrderedDict({t.label: t for t in terms})

    @property
    def bodies(self):
        from amcat.tools.amcates import build_body
        return (dict(build_body(t.query)) for t in self.terms.values())

    def postprocess(self, value):
        return self.terms[value]

    def get_aggregation(self):
        for label, body in zip(self.terms.keys(), self.bodies):
            yield label, {"filter": body}

    def parse_aggregation_result(self, result):
        return result.items()


class IntervalCategory(Category):
    def __init__(self, interval):
        if interval not in ELASTIC_TIME_UNITS:
            err_msg = "{} not a valid interval. Choose on of: {}"
            raise ValueError(err_msg.format(interval, ELASTIC_TIME_UNITS))
        self.interval = interval

    def postprocess(self, value):
        d = datetime.datetime.fromtimestamp(value / 1000)
        return datetime.datetime(d.year, d.month, d.day)

    def get_aggregation(self):
        return {
            "date": {
                "date_histogram": {
                    "field": "date",
                    "interval": self.interval
                }
            }
        }
