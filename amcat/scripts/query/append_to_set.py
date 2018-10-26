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
import json
from django import forms
from django.template import Context
from django.template.loader import get_template

from amcat.models import ArticleSet, Project, Role
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.keywordsearch import SelectionSearch
from amcat.models.authorisation import ROLE_PROJECT_WRITER
from amcat.models.article import _check_read_access

OK_TEMPLATE = get_template("query/ok.html")


class AppendToSetForm(QueryActionForm):
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=True, empty_label=None)
    articleset =  forms.ModelChoiceField(queryset=ArticleSet.objects.none(), required=True, empty_label=None)

    def __init__(self, *args, **kwargs):
        super(AppendToSetForm, self).__init__(*args, **kwargs)

        rw_role = Role.objects.get(id=ROLE_PROJECT_WRITER)
        projects = self.user.userprofile.get_projects(rw_role).distinct()
        self.fields["project"].queryset = projects
        self.fields["project"].initial = self.project

        # This is currently javascript magic hacked into query.js. Generalise?
        self.fields["articleset"].widget.attrs = {
            "class": "depends",
            "data-depends-on": json.dumps(["project"]),
            "data-depends-url": "/api/v4/projects/{project}/favourite_articlesets/?format=json&page_size=10000",
            "data-depends-value": "{id}",
            "data-depends-label": "{name} (id: {id})",
        }

        self.fields["articleset"].queryset = ArticleSet.objects.filter(project__in=projects)


class AppendToSetAction(QueryAction):
    form_class = AppendToSetForm
    output_types = (("text/html", "Result"),)
    required_role = ROLE_PROJECT_WRITER

    def target_project(self, form):
        return form.cleaned_data["project"]
    
    def run(self, form):
        self.monitor.update(10, "Executing query..")
        article_ids = list(SelectionSearch.get_instance(form).get_article_ids())
        _check_read_access(self.user, article_ids)
        self.monitor.update(60, "Saving to set..")
        form.cleaned_data["articleset"].add_articles(article_ids)

        return OK_TEMPLATE.render({
            "project": self.project,
            "aset": form.cleaned_data["articleset"],
            "len": len(article_ids)
        })

