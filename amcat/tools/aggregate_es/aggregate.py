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
from itertools import count, takewhile
__all__ = ("aggregate",)


def flatten(aggregation, categories):
    aggregation = categories.pop(0).parse_aggregation_result(aggregation)

    if not categories:
        for key, aggr in aggregation:
            yield [key, aggr["doc_count"]]
    else:
        for key, sub in aggregation:
            for row in flatten(sub, list(categories)):
                yield [key] + row


def build_aggregate(categories):
    aggregation = dict(categories.pop(0).get_aggregation())

    if categories:
        sub_aggregation = build_aggregate(categories)
        for aggr in aggregation.values():
            aggr["aggregations"] = sub_aggregation

    return aggregation

def build_query(query, filters, categories):
    yield "aggregations", build_aggregate(list(categories))

    if query is not None or filters is not None:
        from amcat.tools.amcates import build_body
        body = build_body(query, filters, query_as_filter=True)
        yield "query", {"constant_score": dict(body)}


def aggregate(query=None, filters=None, categories=(), objects=True, es=None, flat=True):
    from amcat.tools.amcates import ES

    if not categories:
        raise ValueError("You need to specify at least one category.")

    body = dict(build_query(query, filters, categories))
    raw_result = (es or ES()).search(body, search_type="count")
    aggregation = list(flatten(raw_result["aggregations"], list(categories)))

    # Convert to suitable Python value
    for i, category in enumerate(categories):
        for row  in aggregation:
            row[i] = category.postprocess(row[i])

    # Replace ids with model objects
    if objects:
        for i, category in enumerate(categories):
            pks = [row[i] for row in aggregation]
            objs = category.get_objects(pks)
            for row in aggregation:
                row[i] = category.get_object(objs, row[i])

    aggregation = map(tuple, aggregation)

    if not flat:
        aggregation = ((row[:-1], row[-1:]) for row in aggregation)

    aggregation = list(aggregation)

    return aggregation

