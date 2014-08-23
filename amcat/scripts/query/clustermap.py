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
import json
import os

from sh import java
from lxml import html

from base64 import b64encode, b64decode
from StringIO import StringIO
from functools import partial
from tempfile import NamedTemporaryFile
from itertools import chain

from django.template import Context
from django.template.loader import get_template
from django.core.exceptions import ValidationError
from django.conf import settings

from amcat.scripts.query import QueryActionForm, QueryAction, QueryActionHandler
from amcat.tools.keywordsearch import SelectionSearch


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


def aduna(xml_path, img_path):
    stdout, stderr = StringIO(), StringIO()
    _aduna = partial(java, "-classpath", CLASS_PATH, "-Xms%s" % ADUNA_MEMORY, "Cluster")
    _aduna(xml_path, img_path, _err=stderr, _out=stdout).wait()
    stdout, stderr = stdout.getvalue().strip(), stderr.getvalue().strip()

    if not stdout:
        raise AdunaException("Aduna clustermap proces generated error: %s" % stderr)

    return open(img_path).read(), stdout, stderr


class AdunaException(Exception):
    pass


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

        if len(queries) <= 2:
            raise ValidationError("You need to provide at least 2 queries to generate a clustermap")

        return super(ClusterMapForm, self).clean()


def clustermap_html_to_coords(_html):
    doc = html.fromstring(_html)
    for area in doc.cssselect("area"):
        coords = map(int, area.attrib["coords"].split(","))
        article_id = int(area.attrib["href"])
        yield {"coords": coords, "article_id": article_id}


class ClusterMapAction(QueryAction):
    form_class = ClusterMapForm
    task_handler = ClusterMapHandler
    output_types = (
        ("application/json+clustermap", "Inline (interactive)"),
        ("image/png+base64", "Inline (image only)"),
        ("image/png", "PNG"),
    )

    def run(self, form):
        selection = SelectionSearch(form)
        queries = selection.get_article_ids_per_query()
        all_article_ids = chain.from_iterable(queries.values())

        with NamedTemporaryFile(suffix=".xml") as xml:
            xml.write(XML_TEMPLATE.render(Context(locals())))
            xml.flush()
            with NamedTemporaryFile(suffix=".png") as png:
                image, html, _ = aduna(xml.name, png.name)

        if form.cleaned_data["output_type"] == "application/json+clustermap":
            coords = tuple(clustermap_html_to_coords(html))
            return json.dumps({"coords": coords, "image": b64encode(image)})

        # JSON can't encode bytes (celery)
        return b64encode(image)
