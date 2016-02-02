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
Contains functions to create a clustermap. That is, given a bunch of queries,
which groups of articles are in q1, q1 AND q2, etc. Can be used as input for
visualisation software such as:

    http://www.aduna-software.com/technology/clustermap
"""

from __future__ import unicode_literals, print_function, absolute_import

import sh
import os

from collections import defaultdict
from functools import partial
from itertools import chain, product, repeat
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from lxml import html

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# XML template given to Aduna binary
XML_TEMPLATE = get_template("query/clustermap/cluster.xml")

# Location of Aduna binaries
ADUNA_JARS = ("aduna-clustermap-2006.1.jar", "aduna-clustermap-2006.1-resources.jar")
ADUNA_PATH = os.path.join(settings.ROOT, "amcat/contrib/java")
CLASS_PATH = ":".join(chain((ADUNA_PATH,), [
    os.path.join(ADUNA_PATH, jar) for jar in ADUNA_JARS
]))

# Minimal memory allocated by JVM
ADUNA_MEMORY = "1000m"

# Template for interactive clustermap
HTML_TEMPLATE = get_template("query/clustermap/clustermap.html")


### CLUSTER LOGIC ###
def get_product(queries):
    return set(map(frozenset, product(*repeat(tuple(queries), len(queries)))))


def get_intersections(queries):
    """Based on a mapping {query: ids} determine a mapping {[query] -> [ids]}. This
    is different from a clustermap; this function merely determines intersections: an
    article id can exist in multiple sets.

    @param queries.keys(): [SearchQuery]
    @param queries.values(): [int]
    @returns: mapping of cluster (frozenset of queries) to a set of article ids
    """
    queries = {q: set(ids) for q, ids in queries.items()}
    all_article_ids = set(chain.from_iterable(queries.values()))
    clusters = {cluster: all_article_ids.copy() for cluster in get_product(queries.keys())}

    for cluster, cluster_ids in clusters.items():
        for query in cluster:
            cluster_ids &= queries[query]

    return clusters


def get_clusters(queries):
    """Based on a mapping {query: ids} determine a mapping {[query] -> [ids]}, thus
    determining the cluster it belongs to.

    @param queries.keys(): SearchQuery
    @param queries.values(): List of ids
    @returns: mapping of cluster (frozenset of queries) to a set of article ids
    """
    queries = {q: set(ids) for q, ids in queries.items()}

    article_clusters = defaultdict(set)
    for query, aids in queries.items():
        for aid in aids:
            article_clusters[aid].add(query)

    clusters = defaultdict(set)
    for aid, queries in article_clusters.iteritems():
        clusters[frozenset(queries)].add(aid)

    return clusters


def _get_clustermap_table_rows(headers, isects):
    for cluster in get_product(headers):
        yield tuple(int(bool(h in cluster)) for h in headers) + (len(isects[cluster]),)


def get_clustermap_table(queries):
    intersections = get_intersections(queries)
    headers = sorted(queries.keys(), key=lambda q: str(q))
    rows = _get_clustermap_table_rows(headers, intersections)
    return headers + ["Total"], rows


def _get_cluster_query(all_queries, cluster_queries):
    exclude_queries = "(%s)" % ") OR (".join(q.query for q in all_queries - cluster_queries)
    include_queries = "(%s)" % ") AND (".join(q.query for q in cluster_queries)
    return "({include_queries}) NOT ({exclude_queries})".format(**locals()).replace(" NOT (())", "")


def get_cluster_queries(clusters):
    """Based on a collection of clusters (for example those returned by get_clusters()),
    determine the query needed to fetch the articles in that particular cluster.
    """
    all_queries = set(chain.from_iterable(clusters))
    return (_get_cluster_query(all_queries, queries) for queries in clusters)


### ADUNA CLUSTERMAP IMAGE LOGIC ###
class AdunaException(Exception):
    pass


def aduna(xml_path, img_path):
    stdout, stderr = StringIO(), StringIO()
    _aduna = partial(sh.java, "-classpath", CLASS_PATH, "-Xms%s" % ADUNA_MEMORY, "Cluster")
    _aduna(xml_path, img_path, _err=stderr, _out=stdout).wait()
    stdout, stderr = stdout.getvalue().strip(), stderr.getvalue().strip()

    if not stdout:
        raise AdunaException("Aduna clustermap proces generated error: %s" % stderr)

    return open(img_path).read(), stdout, stderr


def clustermap_html_to_coords(_html):
    doc = html.fromstring(_html)
    for area in doc.cssselect("area"):
        coords = map(int, area.attrib["coords"].split(","))
        article_id = int(area.attrib["href"])
        yield {"coords": coords, "article_id": article_id}


def get_clustermap_image(queries):
    """Based on a mapping {query: ids} render an Aduno clustermap.

    @returns: (image bytes, html) """
    all_article_ids = chain.from_iterable(queries.values())

    with NamedTemporaryFile(suffix=".xml") as xml:
        xml.write(XML_TEMPLATE.render(Context(locals())))
        xml.flush()
        with NamedTemporaryFile(suffix=".png") as png:
            return aduna(xml.name, png.name)[:-1]

