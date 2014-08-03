# ##########################################################################
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
import json

import logging

from django.http import HttpResponse

from webscript import WebScript
import amcat.scripts.forms
from amcat.models import Project
from amcat.tools import keywordsearch
from amcat.scripts.forms import SelectionForm

stats_log = logging.getLogger("statistics:" + __name__)
log = logging.getLogger(__name__)

FORM_FIELDS_TO_ELASTIC = {'article_id': "id", "medium_name": "medium", "medium_id": "mediumid",
                          "pagenr": "page"}


class ShowArticleList(WebScript):
    name = "Article List"
    form_template = "api/webscripts/articlelistform.html"
    form = amcat.scripts.forms.ArticleColumnsForm
    output_template = None

    def run(self):
        formData = self.data.copy()  # copy needed since formData is inmutable

        if "articlesets" not in formData:
            artsets = [str(aset.id) for aset in Project.objects.get(id=formData['projects']).all_articlesets()]
            formData.setlist("articlesets", artsets)

        if isinstance(self.data['projects'], (basestring, int)):
            project_id = int(self.data['projects'])
        else:
            project_id = int(self.data['projects'][0])

        formData["start_date"] = formData["start_date"].split("T")[0]
        formData["end_date"] = formData["end_date"].split("T")[0]

        sf = SelectionForm(self.project, formData)
        if not sf.is_valid():
            raise ValueError(dict(sf._errors))

        t = keywordsearch.getDatatable(sf.cleaned_data, rowlink_open_in="new", allow_html_export=True)
        t = t.rowlink_reverse("project-article-details", args=[project_id, '{id}'])
        cols = {FORM_FIELDS_TO_ELASTIC.get(f, f) for f in self.data.getlist('columns')}
        for f in list(t.get_fields()):
            if f not in cols:
                t = t.hide(f)

        if 'kwic' in cols and not self.data.get('query'):
            raise Exception("Cannot provide Keyword in Context without query")

        for col in cols & {'hits', 'text', 'lead', 'kwic'}:
            t = t.add_arguments(col=col)
        html = unicode(t)

        stats_log.info(json.dumps({
            "actions": "query:articlelist", "user": self.user.username,
            "project_id": self.project.id, "project__name": self.project.name
        }))

        if self.output == "html":
            response = HttpResponse(mimetype='text/html')
            response.write(html)
            return response
        else:
            return self.outputJsonHtml(html)

