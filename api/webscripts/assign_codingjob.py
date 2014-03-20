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

import json

from navigator.utils import auth

from django import forms
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.core.urlresolvers import reverse

from webscript import WebScript

from amcat.scripts.actions.create_sentences import CreateSentences
from amcat.scripts.tools import database
from amcat.models.articleset import ArticleSet
from amcat.models.coding.codingschema import CodingSchema
from amcat.models.project import Project
from amcat.models.coding.codingjob import CodingJob
from amcat.models.user import User
from amcat.forms import widgets
from amcat.tools import keywordsearch
from navigator.forms import gen_user_choices

from amcat.scripts.forms import SelectionForm


import logging
log = logging.getLogger(__name__)

class AssignCodingJobForm(forms.Form):
    setname = forms.CharField(max_length=100, label="New set name",
            help_text="This creates a new set and assigns it to selected coder.")

    coder = forms.ChoiceField(widget=widgets.JQuerySelect)
    unitschema = forms.ModelChoiceField(None)
    articleschema = forms.ModelChoiceField(None)
    insertuser = forms.ModelChoiceField(None)
    
    def __init__(self, project=None, skip_existing=False, *args, **kwargs):
        self.skip_existing = skip_existing
        super(AssignCodingJobForm, self).__init__(*args, **kwargs)

        if not project:
            project = Project.objects.get(id=kwargs['data'].get('projects'))

        self.fields['coder'].choices = gen_user_choices(project)
        self.fields['unitschema'].queryset = project.get_codingschemas().filter(isarticleschema=False).distinct()
        self.fields['articleschema'].queryset = project.get_codingschemas().filter(isarticleschema=True).distinct()
        self.fields['insertuser'].queryset = User.objects.all()

        req = auth.get_request()
        if req is not None:
            del self.fields['insertuser']

    def clean_setname(self):
        if not self.skip_existing:
            if ArticleSet.objects.filter(name__iexact=self.cleaned_data['setname']).exists():
                raise forms.ValidationError("Set with this name already exists")

        return self.cleaned_data

class AssignCodingJob(WebScript):
    name = "Assign as codingjob"
    form_template = "api/webscripts/assign_codingjob.html"
    form = AssignCodingJobForm
    displayLocation = ('ShowSummary', 'ShowArticleList')
    output_template = None 
    is_edit = True

    def __init__(self, skip_existing=False, *args,  **kwargs):
        self.skip_existing = skip_existing
        super(AssignCodingJob, self).__init__(*args, **kwargs)

    @classmethod
    def formHtml(cls, project=None):
        form = AssignCodingJobForm(project=project)
        return render_to_string(cls.form_template, locals())

    @classmethod
    def get_called_with(cls, **called_with):
        called_with["skip_existing"] = True
        return called_with

    def get_form(self, **kwargs):
        form = super(AssignCodingJob, self).get_form(skip_existing=self.skip_existing, **kwargs)
        self.data["insertuser"] = self.user.id
        return form

    def run(self):
        sel = SelectionForm(project=self.project, data=self.data)

        if not sel.is_valid():
            # This should not happen when using normal pages (i.e., someone is trying
            # to hack)
            forms.ValidationError("Non-valid values entered.")

        articles = list(keywordsearch.get_ids(self.data))

        # Create articleset
        a = ArticleSet.create_set(project=self.project, articles=articles, name=self.data['setname'], favourite=False)

        # Split all articles 
        CreateSentences(dict(articlesets=[a.id])).run()

        # Create codingjob
        coder = User.objects.get(id=self.data['coder'])
        articleschema = CodingSchema.objects.get(id=self.data['articleschema'])
        unitschema = CodingSchema.objects.get(id=self.data['unitschema'])

        if not 'insertuser' in self.data:
            insertuser = auth.get_request().user
        else:
            insertuser = User.objects.get(id=self.data['insertuser'])

        c = CodingJob.objects.create(project=self.project, name=self.data['setname'], articleset=a,
                                     coder=coder, articleschema=articleschema, unitschema=unitschema,
                                     insertuser=insertuser)
        html = "<div>Saved as <a href='%s'>coding job %s</a>.</div>"


        return HttpResponse(json.dumps({
            "html" : html % (reverse("coding job-details", args=[self.project.id, c.id]), c.id),
            "webscriptClassname" : self.__class__.__name__,
            "webscriptName" : self.name,
            "doNotAddActionToMainForm" : True            
            
        }), mimetype='application/json')

