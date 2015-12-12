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

"""
import urllib
from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import get_template
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.amcates import HASH_FIELDS
from amcat.tools.keywordsearch import SelectionSearch
from api.rest.datatable import Datatable
from api.rest.resources import SearchResource


COLUMNS = ["id"] + sorted(set(HASH_FIELDS) | {"medium"})
TABLE_TEMPLATE = get_template("query/articlelist.html")
ARTICLE_ROWLINK = "{}articles/{}"

API_KEYWORD_MAP = {
    "query": "q",
    "articlesets": "sets",
    "columns": "col",
}


class ArticleListActionForm(QueryActionForm):
    columns = forms.MultipleChoiceField(
        choices=(
            ("Calculated", (("hits", "hits"), ("kwic", "kwic"))),
            ("Properties", [(f, f) for f in COLUMNS])
        ),
        initial=("id", "date", "mediumid", "medium", "headline")
    )

    def clean_columns(self):
        columns = self.cleaned_data["columns"]
        query = self.cleaned_data["query"].strip()

        if "kwic" in columns and not query:
            error_msg = "One or more queries are needed for '{}'"
            raise ValidationError(error_msg.format("kwic"))

        if "hits" in columns and not query:
            error_msg = "One or more queries are needed for '{}'"
            raise ValidationError(error_msg.format("hits"))

        return columns


def get_extra_args(qdict):
    for k, vs in qdict:
        for v in vs:
            yield (k, v)


class ArticleListAction(QueryAction):
    output_types = (("text/html", "HTML"),)
    form_class = ArticleListActionForm

    def run(self, form):
        selection = SelectionSearch(form)
        data = {API_KEYWORD_MAP.get(k, k): v for k,v in self.data.iterlists()}
        data["q"] = ["{}#{}".format(q.label, q.query) for q in selection.get_queries()]
        url = urllib.urlencode(data, doseq=True)
        rowlink = ARTICLE_ROWLINK.format(reverse("navigator:project-details", args=[self.project.id]), "{id}")
        table = Datatable(SearchResource, url="/api/v4/search", rowlink=rowlink, rowlink_open_in="new", checkboxes=True)
        table = table.add_arguments(minimal="1")
        table = table.add_arguments(project=str(self.project.id))

        for k, vs in data.items():
            for v in vs:
                table = table.add_arguments(**{k:v})

        return TABLE_TEMPLATE.render(Context({"form": form, "url": url, "table": table}))
