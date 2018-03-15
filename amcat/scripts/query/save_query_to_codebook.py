###########################################################################
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
import logging

from amcat.models import Codebook, Language, Code
from amcat.scripts.query import QueryAction, QueryActionForm
from amcat.tools.keywordsearch import SelectionSearch
from django import forms
from django.core.exceptions import ValidationError
from django.http import HttpResponse

log = logging.getLogger(__name__)


class SaveQueryToCodebookForm(QueryActionForm):
    existing_codebook = forms.ModelChoiceField(Codebook.objects.none(), required=False)
    new_codebook = forms.CharField(required=False)
    indicator_language = forms.ModelChoiceField(Language.objects.all(), help_text="Label language under which queries are stored.", required=True)
    #delete_obsolete_codes = forms.BooleanField(initial=False, required=False, help_text="Delete codes in (existing) codebook which are not in the current querDelete codes in (existing) codebook which are not in the current query.")

    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)

        self.fields["existing_codebook"].queryset = self.project.get_codebooks()

    def clean(self):
        if self.cleaned_data.get("existing_codebook") and self.cleaned_data.get("new_codebook"):
            raise ValidationError("You cannot select both an existing codebook and a new codebook", code="invalid")
        return self.cleaned_data


class SaveQueryToCodebookAction(QueryAction):
    output_types = (("text/html", "Inline"),)
    form_class = SaveQueryToCodebookForm

    def run(self, form):
        # Get codebook object
        new_codebook = form.cleaned_data["new_codebook"]
        if new_codebook:
            codebook = Codebook(name=new_codebook, project=self.project)
            codebook.save()
        else:
            codebook = form.cleaned_data["existing_codebook"]
            codebook.cache()

        # Get queries and their labels
        indicator_language = form.cleaned_data["indicator_language"]
        roots = {r.label: r for r in codebook.get_roots()}
        queries = {q.label: q for q in SelectionSearch.get_instance(form).get_queries()}

        updated, new = 0, 0
        for label, query in queries.items():
            if label in roots:
                # Update existing code
                roots[label].add_label(indicator_language, query.query, replace=True)
                updated += 1
            else:
                # Create new code
                code = Code(label=label)
                code.save()
                code.add_label(indicator_language, query.query, replace=True)
                codebook.add_code(code)
                new += 1

        return "Updated {} code(s), added {} new code(s).".format(updated, new)
