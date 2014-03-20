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
import base64

from django import forms

from django.forms import Textarea, ModelForm, HiddenInput

from django.views.generic.base import (View, TemplateResponseMixin)
from django.views.generic.detail import SingleObjectMixin

from django.forms.formsets import formset_factory
from django.forms.models import BaseModelFormSet
from django.forms.models import modelform_factory
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from navigator.views.datatableview import DatatableCreateView
from navigator.views.projectview import ProjectListBaseView, ProjectDetailView
from navigator.views.article_views import ArticleSetArticleDetailsView
from navigator.views.datatableview import DatatableMixin

from amcat.models import RuleSet, Rule, Codebook, Code, Language
from amcat.tools import amcatxtas


class RuleSetTableView(DatatableCreateView):
    model = RuleSet
    rowlink_urlname = "ruleset"


def _normalize(x):
    for quote in u'\x91\x92\x82\u2018\u2019\u201a\u201b\xab\xbb\xb0':
        x = x.replace(quote, "'")
    for quote in u'\x93\x94\x84\u201c\u201d\u201e\u201f\xa8':
        x = x.replace(quote, '"')
    return x


class RuleForm(ModelForm):

    class Meta:
        model = Rule
        fields = ["id", "ruleset", "order", "label",
                  "display", "where", "insert", "remove", "remarks"]
        widgets = {field: Textarea(attrs={'cols': 5, 'rows': 4})
                   for field in ["insert", "remove", "where", "remarks"]}
        widgets["ruleset"] = HiddenInput


class UploadRulesForm(forms.Form):
    file  = forms.FileField()

class RuleSetView(View, TemplateResponseMixin, SingleObjectMixin):
    model = RuleSet
    template_name = "ruleset.html"

    def get(self, request, pk, **kwargs):
        self.object = self.get_object()

        ruleset_form = modelform_factory(RuleSet)(instance=self.object)

        formset = formset_factory(RuleForm, formset=BaseModelFormSet,
                                  can_delete=True)
        formset.model = Rule
        formset = formset(queryset=self.object.rules.all())

        ruleset_json = json.dumps(self.object.get_ruleset(), indent=4)

        upload_form = UploadRulesForm

        ctx = self.get_context_data(
            codebook = self.object.lexicon_codebook,
            ruleset_form = ruleset_form,
            ruleset_json = ruleset_json,
            formset = formset,
            upload_form = upload_form)

        return self.render_to_response(ctx)

    def post(self, request, pk, **kwargs):
        self.object = self.get_object()
        ruleset = self.object.id

        class _RuleFormWithRuleset(RuleForm):

            """Rule Form that inserts ruleset info"""

            def clean(self):
                # HACK! How to add ruleset info to extra fields?
                cleaned_data = super(RuleForm, self).clean()
                msg_req = u"This field is required."
                if (("ruleset" not in cleaned_data
                     and len(self._errors.get("ruleset", [])) == 1
                     and self._errors["ruleset"][0] == msg_req)):
                    cleaned_data["ruleset"] = RuleSet.objects.get(pk=ruleset)
                    del self._errors["ruleset"]
                for fld in ("insert", "remove", "where"):
                    self.cleaned_data[fld] = _normalize(self.cleaned_data[fld])
                return cleaned_data

        if request.FILES:
            # upload json dump
            ruleset = json.load(request.FILES['file'])
            if not 'rules' in ruleset and 'lexicon' in ruleset:
                raise ValidationError("Invalid json")
            rules = [dict(label = rule.get('label', 'rule-{}'.format(i)),
                          ruleset = self.object,
                          order =  int(rule.get('order', i)),
                          where = rule['condition'],
                          insert = rule.get('insert', ''),
                          remove = rule.get('remove', ''),
                          remarks = rule.get('remarks', ''),
                          ) for (i, rule) in enumerate(ruleset['rules'])]

            lexicon = {}
            for entry in ruleset['lexicon']:
                lexicon[entry['lexclass']] = entry['lemma']

            self.object.rules.all().delete()
            cb = self.object.lexicon_codebook
            Code.objects.filter(codebook_codes__codebook_id=cb.id).delete()
            cb.codebookcodes.all().delete()
            lexlang = self.object.lexicon_language
            lang = Language.objects.get(pk=(0 if lexlang.id == 1 else 1))
            for lexclass, lemmata in lexicon.iteritems():
                c = Code.create(lexclass, lang)
                c.add_label(lexlang, ", ".join(lemmata))
                cb.add_code(c)

            for rule in rules:
                Rule.objects.create(**rule)


            return redirect(reverse("ruleset", args=(self.object.id, )))
        else:
            ruleset_form = modelform_factory(RuleSet)(
                request.POST, instance=self.object)
            if ruleset_form.is_valid():
                ruleset_form.save()

        formset = formset_factory(_RuleFormWithRuleset,
                                  formset=BaseModelFormSet, can_delete=True)
        formset.model = Rule
        formset = formset(request.POST, request.FILES,
                          queryset=self.object.rules.all())
        if formset.is_valid():
            formset.save()

            return redirect(reverse("ruleset", args=(self.object.id, )))

            formset = formset_factory(RuleForm, formset=BaseModelFormSet,
                                      can_delete=True)
            formset.model = Rule
            formset = formset(queryset=self.object.rules.all())


        ctx = self.get_context_data(formset=formset, ruleset_form=ruleset_form)
        return self.render_to_response(ctx)


class ArticleRuleListView(ProjectListBaseView, DatatableMixin):
    model = RuleSet
    parent = ArticleSetArticleDetailsView
    rowlink = './{id}'


class ArticleRuleDetailsView(ProjectDetailView):
    model = RuleSet
    parent = ArticleRuleListView

    def get_sentences(self, saf):
        for sid in sorted(set(t['sentence'] for t in saf['tokens'])):
            stokens = (t['word']
                       for t in sorted(saf['tokens'],
                                       key=lambda t: int(t['offset']))
                       if t['sentence'] == sid)
            yield sid, " ".join(stokens)

    def get_context_data(self, **kwargs):
        from syntaxrules.syntaxtree import SyntaxTree
        from syntaxrules.soh import SOHServer

        ctx = super(ArticleRuleDetailsView, self).get_context_data(**kwargs)
        saf = amcatxtas.get_result(int(self.kwargs['article_id']),
                                   self.object.preprocessing)
        sid = int(self.request.GET.get("sid", 1))
        sentences = list(self.get_sentences(saf))

        soh = SOHServer(url="http://localhost:3030/x")
        t = SyntaxTree(soh)
        t.load_saf(saf, sid)
        g = t.get_graphviz()
        original_tree = base64.b64encode(g.draw(format='png', prog='dot'))

        ruleset = self.object.get_ruleset()
        t.apply_ruleset(ruleset)
        g = t.get_graphviz(grey_rel=True)
        processed_tree = base64.b64encode(g.draw(format='png', prog='dot'))

        ruleset_dump = json.dumps(ruleset, indent=2)
        saf_dump = json.dumps(saf, indent=2)
        ctx.update(locals())
        return ctx
