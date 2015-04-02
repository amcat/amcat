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
from __future__ import unicode_literals, print_function
import csv
import json
from base64 import b64encode, b64decode
import StringIO
import traceback

from django.core.exceptions import ValidationError

from amcat.scripts.query import QueryActionForm, QueryAction, QueryActionHandler
from amcat.tools.clustermap import get_clustermap_image, clustermap_html_to_coords, get_clusters, get_cluster_queries, \
    get_clustermap_table
from amcat.tools.keywordsearch import SelectionSearch


class ClusterMapHandler(QueryActionHandler):
    def get_result(self):
        result = super(ClusterMapHandler, self).get_result()
        if self.task.arguments["data"]["output_type"][0] == "image/png":
            return b64decode(result)
        return result


class ClusterMapForm(QueryActionForm):
    def clean(self):
        queries = self.cleaned_data["query"].split("\n")
        queries = filter(bool, map(unicode.strip, queries))

        if len(queries) < 2:
            raise ValidationError("You need to provide at least 2 queries to generate a clustermap")

        return super(ClusterMapForm, self).clean()


class ClusterMapAction(QueryAction):
    form_class = ClusterMapForm
    task_handler = ClusterMapHandler
    output_types = (
        ("application/json+clustermap", "Aduna"),
        ("application/json+clustermap+table", "Table"),
        ("text/csv", "CSV"),
        ("text/csv", "CSV (Excel)"),
        ("text/csv+tab", "CSV (tab-separated)"),
    )

    def run(self, form):
        selection = SelectionSearch(form)
        queries = selection.get_article_ids_per_query()

        if form.cleaned_data["output_type"] == "application/json+clustermap":
            clusters, articles = zip(*get_clusters(queries).items())
            cluster_queries = get_cluster_queries(clusters)
            image, html = get_clustermap_image(queries)
            coords = tuple(clustermap_html_to_coords(html))

            return json.dumps(
                {"coords": coords, "image": b64encode(image),
                 "clusters": [
                     {"query": q, "articles": tuple(a)}
                     for q, a in zip(cluster_queries, articles)
                 ]}
            )

        dialect = 'excel'
        if form.cleaned_data["output_type"] == "text/csv+tab":
            dialect = 'excel-tab'

        result = StringIO.StringIO()
        headers, rows = get_clustermap_table(queries)
        csvf = csv.writer(result, dialect=dialect)
        csvf.writerow(map(str, headers))
        csvf.writerows(sorted(rows))

        if form.cleaned_data["output_type"] == "application/json+clustermap+table":
            return json.dumps({
                "csv": result.getvalue(),
                "queries": {q.label: q.query for q in queries}
            })

        return result.getvalue()


