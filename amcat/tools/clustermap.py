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

import os
import subprocess

from collections import defaultdict, OrderedDict
from itertools import chain
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
def combinations(iterable):
    """
    Returns a generator yielding all combinations of all lengths of `iterable` as tuples.
    Care should be taken, as there are 2^n of these combinations.
    """
    all = tuple(iterable)
    if len(all) == 0:
        yield ()
        return
    head, tail = all[0], all[1:]
    for result in combinations(tail):
        yield (head,) + result
        yield result

def get_clusters(queries) -> dict:
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
    for aid, queries in article_clusters.items():
        clusters[frozenset(queries)].add(aid)

    return clusters


def get_clustermap_table(queries):
    """
    Given a mapping of query to ids, return a table with the #hits for each boolean combination
    """
    queries = OrderedDict((k, set(v)) for (k,v) in queries.items())
    header = sorted(queries.keys(), key=lambda q: str(q))
    rows = []
    allids = set(chain.from_iterable(queries.values()))
    for c in combinations(header):
        ids = allids.copy()
        row = []
        for q in header:
            row.append(int(q in c))
            if q in c:
                ids &= queries[q]
            else:
                ids -= queries[q]
        n = len(ids)
        if n:
            rows.append(tuple(row + [n]))

    return [h.label for h in header] + ["Total"], rows


def _get_cluster_query(all_queries, cluster_queries):
    # We sort the queries to generate the queries in a deterministic manner
    exclude_queries = "(%s)" % ") OR (".join(sorted(q.query for q in all_queries - cluster_queries))
    include_queries = "(%s)" % ") AND (".join(sorted(q.query for q in cluster_queries))
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
    args = ["java", "-classpath", CLASS_PATH, "-Xms%s" % ADUNA_MEMORY, "Cluster", xml_path, img_path]
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
    except FileNotFoundError:
        raise AdunaException("Java executable not found")


    if not stdout:
        raise AdunaException("Aduna clustermap proces generated error: %s" % stderr)

    return open(img_path, "rb").read(), stdout, stderr


def clustermap_html_to_coords(_html):
    doc = html.fromstring(_html)
    for area in doc.cssselect("area"):
        coords = list(map(int, area.attrib["coords"].split(",")))
        article_id = int(area.attrib["href"])
        yield {"coords": coords, "article_id": article_id}


def get_clustermap_image(queries):
    """Based on a mapping {query: ids} render an Aduno clustermap.

    @returns: (image bytes, html) """
    all_article_ids = list(chain.from_iterable(queries.values()))

    with NamedTemporaryFile(suffix=".xml", mode="wb") as xml:
        context = locals()
        rendered = XML_TEMPLATE.render(context)
        xml.write(rendered.encode('utf-8'))
        xml.flush()
        with NamedTemporaryFile(suffix=".png") as png:
            return aduna(xml.name, png.name)[:-1]
