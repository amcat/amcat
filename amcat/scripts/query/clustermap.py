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

import csv
import json
from base64 import b64encode

from django.core.exceptions import ValidationError

from amcat.scripts.query import QueryActionForm, QueryAction, QueryActionHandler
from amcat.tools.clustermap import get_clustermap_image, clustermap_html_to_coords, get_clusters, get_cluster_queries, \
    get_clustermap_table
from amcat.tools.keywordsearch import SelectionSearch
from amcat.tools.table.table2spss import table2sav
from amcat.tools.table.table3 import Table

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class ClusterMapHandler(QueryActionHandler):
    def get_result(self):
        result = super(ClusterMapHandler, self).get_result()
        if self.task.arguments["data"]["output_type"][0] == "application/spss-sav":
            return open(result, "rb").read()
        return result


class ClusterMapForm(QueryActionForm):
    def clean(self):
        queries = self.cleaned_data["query"].split("\n")
        queries = list(filter(bool, map(str.strip, queries)))

        if len(queries) < 2:
            raise ValidationError("You need to provide at least 2 queries to generate a clustermap")

        return super(ClusterMapForm, self).clean()


class ClusterMapAction(QueryAction):
    form_class = ClusterMapForm
    task_handler = ClusterMapHandler
    output_types = (
        ("application/json+clustermap", "Diagram"),
        ("application/json+clustermap+table", "Table"),
        ("text/csv", "CSV"),
        ("text/csv", "CSV (Excel)"),
        ("text/csv+tab", "CSV (tab-separated)"),
        ("application/spss-sav", "SPSS")
    )

    def run(self, form):
        selection = SelectionSearch.get_instance(form)
        queries = selection.get_article_ids_per_query()

        if form.cleaned_data["output_type"] == "application/json+clustermap":
            try:
                clusters, articles = zip(*get_clusters(queries).items())
            except ValueError as e:
                raise ValueError("Cannot build clustermap of empty query result.")

            cluster_queries = get_cluster_queries(clusters)
            image, html = get_clustermap_image(queries)
            coords = tuple(clustermap_html_to_coords(html))

            return json.dumps(
                {"coords": coords, "image": b64encode(image).decode("ascii"),
                 "clusters": [
                     {"query": q, "articles": tuple(a)}
                     for q, a in zip(cluster_queries, articles)
                 ]}
            )

        headers, rows = get_clustermap_table(queries)

        if form.cleaned_data["output_type"] == "application/spss-sav":
            # *sigh*.. this code is fugly.
            _headers = {str(h): i for i, h in enumerate(headers)}

            return table2sav(Table(
                rows=list(rows),
                columns=list(map(str, headers)),
                columnTypes=[int]*len(headers),
                cellfunc=lambda row, col: row[_headers[col]]
            ))

        dialect = 'excel'
        if form.cleaned_data["output_type"] == "text/csv+tab":
            dialect = 'excel-tab'

        result = StringIO()
        csvf = csv.writer(result, dialect=dialect)
        csvf.writerow(list(map(str, headers)))
        csvf.writerows(sorted(rows))

        if form.cleaned_data["output_type"] == "application/json+clustermap+table":
            return json.dumps({
                "csv": result.getvalue(),
                "queries": {q.label: q.query for q in queries}
            })

        return result.getvalue()


