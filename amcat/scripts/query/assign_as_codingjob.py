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
from django.contrib.auth.models import User

from amcat.models import CodingJob, CodingSchema
from amcat.models.coding.codingjob import _create_codingjob_batches
from amcat.scripts.query import QueryAction
from amcat.scripts.query.saveset import SaveAsSetForm
from amcat.tools.keywordsearch import SelectionSearch


class AssignAsCodingjobForm(SaveAsSetForm):
    job_size = forms.IntegerField(min_value=0, initial=0, help_text="Leave zero for single batch.")
    coder = forms.ModelChoiceField(User.objects.none(), required=True)
    unitschema = forms.ModelChoiceField(CodingSchema.objects.none(), required=False)
    articleschema = forms.ModelChoiceField(CodingSchema.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super(AssignAsCodingjobForm, self).__init__(*args, **kwargs)

        codingschemas = self.project.get_codingschemas()
        self.fields["coder"].queryset = User.objects.filter(id__in=[u.id for u in self.project.users])
        self.fields["articleschema"].queryset = codingschemas.filter(isarticleschema=True)
        self.fields["unitschema"].queryset = codingschemas.filter(isarticleschema=False)


class AssignAsCodingjobAction(QueryAction):
    """
    If a job size is specified, the articles will be split into chunks of this size
    and a separate codingjob will be made for each of the chunks.
    """
    form_class = AssignAsCodingjobForm
    output_types = (("text/html", "Result"),)

    def run(self, form):
        provenance = None#form.cleaned_data["provenance"] #TODO: is dit correct?
        job_size = form.cleaned_data["job_size"]

        self.monitor.update(10, "Executing query..")
        article_ids = list(SelectionSearch.get_instance(form).get_article_ids())

        cj = CodingJob()
        cj.project = self.project
        cj.name = form.cleaned_data["name"]
        cj.unitschema = form.cleaned_data["unitschema"]
        cj.articleschema = form.cleaned_data["articleschema"]
        cj.coder = form.cleaned_data["coder"]
        cj.insertuser = self.user

        self.monitor.update(50, "Creating codingjobs..")

        if job_size == 0:
            job_size = len(article_ids)

        n_batches = len(article_ids) // job_size
        n_batches += 1 if len(article_ids) % job_size else 0
        
        for i, cid in enumerate(_create_codingjob_batches(cj, article_ids, job_size)):
            progress = int((i / float(n_batches)) * (100 // 2))
            msg = "Creating codingjob {} of {}..".format(i+1, n_batches)
            print(50 + progress)
            self.monitor.update(50 + progress, msg)

            if provenance:
                cj = CodingJob.objects.get(id=cid)
                cj.provenance = provenance
                cj.save()

        return "Codingjob(s) created."

