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

from django.forms import Textarea, ModelForm, HiddenInput

from django.core.urlresolvers import reverse
from django.views.generic.base import View, TemplateResponseMixin, ContextMixin, TemplateView
from django.views.generic.detail import SingleObjectMixin

from amcat.models import RuleSet, Rule
from django.forms.formsets import formset_factory
from django.forms.models import BaseModelFormSet
from django.forms.models import modelform_factory

from api.rest.resources import ProjectResource as RuleSetResource
from navigator.views.datatableview import DatatableCreateView

    
class RuleSetTableView(DatatableCreateView):
    model = RuleSet
    rowlink_urlname = "ruleset"

def _normalize_quotes(x):
    for quote in u'\x91\x92\x82\u2018\u2019\u201a\u201b\xab\xbb\xb0':
        x = x.replace(quote, "'")
    for quote in u'\x93\x94\x84\u201c\u201d\u201e\u201f\xa8':
        x= x.replace(quote, '"')
    return x
    
class RuleForm(ModelForm):
    class Meta:
        model = Rule
        fields = ["id", "ruleset", "order", "label", "display", "where", "insert", "remove", "remarks"]
        widgets = {field : Textarea(attrs={'cols': 5, 'rows': 4})
                   for field in ["insert","remove","where","remarks"]}
        widgets["ruleset"] = HiddenInput
    
class RuleSetView(View, TemplateResponseMixin, SingleObjectMixin):
    model = RuleSet
    template_name = "navigator/rule/ruleset.html"

    def get(self, request, pk, **kwargs):
        self.object = self.get_object()

        ruleset_form = modelform_factory(RuleSet)(instance=self.object)
        
        formset = formset_factory(RuleForm, formset=BaseModelFormSet, can_delete=True)
        formset.model = Rule
        formset = formset(queryset=self.object.rules.all())
        
        return self.render_to_response(self.get_context_data(formset=formset, ruleset_form=ruleset_form))
    
    def post(self, request, pk, **kwargs):
        self.object = self.get_object()
        ruleset_id = self.object.id
        class RuleFormWithRuleset(RuleForm):
            def clean(self):
                # HACK! How to add ruleset info to extra fields in a meaningful way?
                cleaned_data = super(RuleForm, self).clean()
                if "ruleset" not in cleaned_data and len(self._errors.get("ruleset", [])) == 1 and self._errors["ruleset"][0] == u"This field is required.":
                    cleaned_data["ruleset"] = RuleSet.objects.get(pk=ruleset_id)
                    del self._errors["ruleset"]
                for field in ("insert", "remove", "where"):
                    self.cleaned_data[field] = _normalize_quotes(self.cleaned_data[field])
                return cleaned_data
            
        ruleset_form = modelform_factory(RuleSet)(request.POST, instance=self.object)
        if ruleset_form.is_valid():
            ruleset_form.save()
        
        formset = formset_factory(RuleFormWithRuleset, formset=BaseModelFormSet, can_delete=True)
        formset.model = Rule
        formset = formset(request.POST, request.FILES, queryset=self.object.rules.all())
        if formset.is_valid():
            formset.save()
            formset = formset_factory(RuleForm, formset=BaseModelFormSet, can_delete=True)
            formset.model = Rule
            formset = formset(queryset=self.object.rules.all())


        return self.render_to_response(self.get_context_data(formset=formset, ruleset_form=ruleset_form))
