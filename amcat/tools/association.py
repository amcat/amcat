##########################################################################
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

"""
An association represents a table of conditional probabilities for a set
of SearchQuery objects.
"""
import datetime

from collections import namedtuple, defaultdict
from functools import partial
from itertools import product

from amcat.tools import amcates
from amcat.tools.caching import cached

from . import dot

ArticleScore = namedtuple("ArticleScore", ["id", "query", "interval", "score"])
ArticleAssociation = namedtuple("ArticleAssociation", ["interval", "probability", "of", "given"])

def format_func(f):
    def ff(float_or_string):
        if isinstance(float_or_string, str):
            return float_or_string
        return f(float_or_string)
    return ff


FORMATS = {
    "0.12": format_func("{:1.2f}".format),
    "0.123": format_func("{:1.3f}".format),
    "12%": format_func(lambda p: "{:1.0f}%".format(p*100)),
    "12.3%": format_func(lambda p: "{:1.1f}%".format(p*100))
}


INTERVALS = {None, "year", "month", "week"}


def get_trivial_weight(result):
    return 1.0


def get_asymptotic_weight(result):
    """
    Asymptotic quadratic weight function.
    @type result: SearchResult
    """
    return 1 - (0.5 ** result.score)


def get_node(queries, query):
    nid = "node_{}_{}".format(len(queries), query.label)
    return dot.Node(nid, query.label)


class Intervals(object):
    @classmethod
    def trivial(cls, date):
        return None

    @classmethod
    def year(cls, date):
        return "{date.year}-01-01".format(date=date)

    @classmethod
    def month(cls, date):
        return "{date.year}-{date.month:02}-01".format(date=date)

    @classmethod
    def quarter(cls, date):
        quarter = 1 + (date.month-1) / 3
        return "{date.year}-{quarter}".format(date=date, quarter=quarter)

    @classmethod
    def week(cls, date):
        date = date + datetime.timedelta(days=-date.weekday())
        return "{date.year}-{date.month:02}-{date.day:02}".format(date=date)

    @classmethod
    def get(cls, interval):
        if interval not in INTERVALS:
            error_msg = "{} is not a valid interval. Choose from: {}"
            raise ValueError(error_msg.format(interval, INTERVALS))

        if interval is None:
            return cls.trivial

        return getattr(cls, interval)


class Association(object):
    """

    """
    def __init__(self, queries, filters, interval=None, weighted=False):
        """
        @type queries: [SearchQuery]
        @type interval: str
        @type weighted: bool
        """
        self.interval = interval
        self.weighted = weighted
        self.queries = queries
        self.filters = filters

        self.fields = ["date"] if interval else []
        self.elastic_api = amcates.ES()
        self.score_func = get_trivial_weight
        self.interval_func = Intervals.get(interval)

        if weighted:
            self.score_func = get_asymptotic_weight

    def _get_query_arguments(self, query):
        return {
            "score": self.weighted,
            "_source": self.fields,
            "filters": self.filters,
            "query": query.query
        }

    def _get_query(self, query):
        return self.elastic_api.query_all(**self._get_query_arguments(query))

    def _get_scores(self):
        # Ideally, we would like to use elastic aggregations for the
        # intervals, but we need scores simultaneously so we can't.
        for query in self.queries:
            for a in self._get_query(query):
                interval = self.interval_func(getattr(a, "date", None))
                yield ArticleScore(a.id, query, interval, self.score_func(a))

    @cached
    def get_scores(self):
        return tuple(self._get_scores())

    @cached
    def get_intervals(self):
        return sorted(set(s.interval for s in self.get_scores()))

    @cached
    def get_queries(self):
        return tuple(sorted(self.queries, key=lambda q: q.label))

    def _get_conditional_probabilities(self):
        """
        @return: [ArticleAssociation]
        """
        probs = defaultdict(partial(defaultdict, dict))
        for aid, query, interval, score in self.get_scores():
            probs[interval][query][aid] = score

        for interval, queries in probs.items():
            for query1, query2 in product(queries, queries):
                sumprob1 = sum(queries[query1].values())

                if query1 == query2:
                    yield ArticleAssociation(interval, 1.0, query1, query2)
                    continue

                if sumprob1 == 0:
                    yield ArticleAssociation(interval, "-", query1, query2)
                    continue

                sumprob2 = 0
                for aid, p1 in queries[query1].items():
                    try:
                        sumprob2 += p1 * queries[query2][aid]
                    except KeyError:
                        continue

                #                                  probability          of      given
                yield ArticleAssociation(interval, sumprob2 / sumprob1, query1, query2)

    @cached
    def get_conditional_probabilities(self):
        return tuple(self._get_conditional_probabilities())

    def _get_table(self, format):
        # Get conditional probabilities and sort on interval / query labels
        probs = self.get_conditional_probabilities()
        probs = sorted(probs, key=lambda aa: (aa.interval, aa.of.label, aa.given.label))

        for interval, probability, of, given in probs:
            if of == given:
                continue
            yield interval, of, given, format(probability)

    def get_table(self, format=str):
        """Render associations as table.

        @param format: function which renders probabilities. Should take a float and return a string
        @return: (headers, rows)"""
        return ["Interval", "From", "To", "Association"], self._get_table(format)

    def _get_crosstable(self, probs, format):
        yield ("",) + self.get_queries()
        for q1 in self.get_queries():
            yield (q1,) + tuple(format(probs[q1][q2]) for q2 in self.get_queries())

    def get_crosstables(self, format=str):
        probabilities = defaultdict(partial(defaultdict, partial(defaultdict, lambda: "-")))

        for aa in self.get_conditional_probabilities():
            probabilities[aa.interval][aa.of][aa.given] = aa.probability

        for interval, probs in sorted(probabilities.items()):
            yield (interval, self._get_crosstable(probs, format))


    def _get_graph(self, format, threshold, include_labels, associations):
        graph = dot.Graph()

        queries = self.get_queries()
        nodes = {query: get_node(queries, query) for query in queries}

        for _, p, of, given in associations:
            if isinstance(p, str) or p <= threshold or of == given or p == 0.0:
                continue

            label = format(p) if include_labels else ""
            graph.addEdge(nodes[of], nodes[given], weight=1+10*p, label=label)

        graph.normalizeWeights()
        return graph

    def get_graphs(self, format=str, threshold=-1, include_labels=False):
        probs = defaultdict(list)
        for aa in self.get_conditional_probabilities():
            probs[aa.interval].append(aa)

        for interval, aas in sorted(probs.items()):
            yield interval, self._get_graph(format, threshold, include_labels, aas)
