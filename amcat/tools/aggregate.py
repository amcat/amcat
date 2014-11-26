###########################################################################
# (C) Vrije Universiteit, Amsterdam (the Netherlands)                     #
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
Contains all logic for
"""

# We might want to be a bit more clever here: we assume querying per medium / term is always
# more efficient than querying per interval. This is not true for a large amount of mediums and
# a small amount of dates (status reports for scrapers tend to have this).
from operator import itemgetter
from amcat.models import Medium
from amcat.tools.amcates import ES
from amcat.tools.toolkit import DefaultOrderedDict
from collections import OrderedDict

import logging
log = logging.getLogger(__name__)


VALID_X_AXES = {"medium", "term"}
VALID_Y_AXES = {"date", "total"}

# We can call transpose() on 'invalid' x / y axes.
VALID_AXES = VALID_X_AXES | VALID_Y_AXES

# Natively supported by elasticsearch.
VALID_INTERVALS = {'year', 'quarter', 'month', 'week', 'day'}

class OrderedSet(OrderedDict):
    # Sorry!
    def add(self, key):
        if key not in self:
            self[key] = None

class DataTable(dict):
    """
    Class that represents a x-by-y table, ie a matrix with column and row headers
    """
    def __init__(self, *args, **kargs):
        self.es = ES()
        self.rows = kargs.pop("rows", OrderedSet())
        self.columns = kargs.pop("columns", OrderedSet())
        super(DataTable, self).__init__(*args, **kargs)

    def __setitem__(self, index, value):
        row, column = index
        self.rows.add(row)
        self.columns.add(column)
        super(DataTable, self).__setitem__(index, value)

    def query_row(self, row, query, filters, group_by=None, interval="month"):
        if group_by is None:
            self[row, "#"] = self.es.count(query, filters)
        else:
            for col, val in self.es.aggregate_query(query, filters, group_by, interval):
                self[row, col] = val

    def to_json(self):
        """Render to json format expected by js/highcharts"""
        for row in self.rows:
            yield row, tuple((col, self[row, col]) for col in self.columns if (row, col) in self)

    def to_table(self, default=0):
        """Render a two dimensional (non-sparse) table as a sequence-of-tuples"""
        t = transpose(self) # WvA: why should to_table always transpose?
        yield ("",) + tuple(t.columns)
        for row in t.rows:
            yield (row,) + tuple(t.get((row, col), default) for col in t.columns)


def transpose(table):
    d = {(col, row): val for ((row, col), val) in table.iteritems()}
    return DataTable(d, rows=table.columns, columns=table.rows)


def aggregate_by_medium(query, filters, group_by=None, interval="month"):
    """
    :param query:
    :param filters:
    :param group_by:
    :param interval:
    :return:
    """
    result = DataTable()
    for medium_id in sorted(result.es.list_media(query, filters)):
        filters["mediumid"] = [medium_id]
        result.query_row(medium_id, query, filters, group_by, interval)
    return result


def aggregate_by_term(queries, filters, group_by=None, interval="month"):
    """

    :param queries:
    :param filters:
    :param group_by:
    :param interval:
    :return:
    """
    result = DataTable()
    queries = (q for q in queries if q.declared_label is not None)
    queries = ((q.label, q.query) for q in queries)
    for term, query in queries:
        result.query_row(term, query, filters, group_by, interval)
    return result


def _aggregate(query, queries, filters, x_axis, y_axis, interval="month"):
    # 'Total' means a 1D aggregation
    y_axis = None if y_axis == "total" else y_axis

    if x_axis == "medium":
        return aggregate_by_medium(query, filters, y_axis, interval)

    if x_axis == "term":
        return aggregate_by_term(queries, filters, y_axis, interval)

    if y_axis is None:
        # We can always aggregate if we just aggregate on total count
        result = DataTable()
        result.query_row("#", query, filters, x_axis, interval)
        return result

    raise ValueError("Invalid axes {x_axis!r}/{y_axis!r}".format(**locals()))


def aggregate(query, queries, filters, x_axis, y_axis, interval="month"):
    """
    Elasticsearch doesn't support aggregating on two variables by default, so we need to
    work around it by querying multiple times for each point on `x_axis`.

    :param query: full query
    :type query: unicode, str

    :param queries: splitted query
    :type queries: list of SearchQuery

    :param filters: filters for elasticsearch (see: ES.query)
    :type filters: dict

    :param x_axis:
    :param y_axis:

    :return:
    """
    if x_axis not in VALID_AXES:
        raise ValueError("{x_axis} is not a valid axis. Choose one of: {VALID_AXES}"
                         .format(**dict(globals(), **locals())))

    if y_axis not in VALID_AXES:
        raise ValueError("{y_axis} is not a valid axis. Choose one of: {VALID_AXES}"
                         .format(**dict(globals(), **locals())))

    if x_axis == y_axis:
        raise ValueError("y_axis and x_axis cannot be the same")

    # We need to transpose the result matrix if x/y is invalid but y/x is valid 
    needs_transposing = (x_axis == "total") or (x_axis not in VALID_X_AXES and y_axis in VALID_X_AXES)

    if needs_transposing:
        aggr = transpose(_aggregate(query, queries, filters, y_axis, x_axis, interval))
    else:
        aggr = _aggregate(query, queries, filters, x_axis, y_axis, interval)

    return aggr.to_json()

# Unittests: amcat.tools.tests.aggregate
