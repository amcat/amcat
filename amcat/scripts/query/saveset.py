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
from django import forms
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from amcat.models import ArticleSet

from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.keywordsearch import SelectionSearch


OK_TEMPLATE = get_template("query/saveset/ok.html")


class SaveAsSetForm(QueryActionForm):
    name = forms.CharField(required=True)
    provenance = forms.CharField(required=False)

    def clean_name(self):
        new_name = self.cleaned_data["name"]

        all_articlesets = self.project.articlesets_set.all()
        if all_articlesets.filter(name__iexact=new_name).exists():
            error_msg = "An articleset called {} already exists."
            raise ValidationError(error_msg.format(self.cleaned_data["name"]))

        return new_name


class SaveAsSetAction(QueryAction):
    form_class = SaveAsSetForm
    output_types = (("text/html", "Result"),)

    def run(self, form):
        name = form.cleaned_data["name"]
        provenance = form.cleaned_data["provenance"]
        aset = ArticleSet.objects.create(name=name, provenance=provenance, project=self.project)
        self.monitor.update(10, "Executing query..")
        article_ids = list(SelectionSearch(form).get_article_ids())
        self.monitor.update(60, "Saving to set..")
        aset.add_articles(article_ids)

        return OK_TEMPLATE.render(Context({
            "project": self.project,
            "aset": aset,
            "len": len(article_ids)
        }))

