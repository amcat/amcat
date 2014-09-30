from saf.clause import *
from saf.saf import SAF
import json

from django.views.generic.edit import FormView
from django import forms

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from navigator.views.project_views import ProjectDetailsView
from amcat.tools.amcatxtas import get_adhoc_result
from amcat.models import Codebook
from itertools import chain

def flatten(listOfLists):
    "Flatten one level of nesting - https://docs.python.org/2/library/itertools.html"
    return chain.from_iterable(listOfLists)

class ClauseView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, FormView):
    class form_class(forms.Form):
        sentence = forms.CharField(label='Sentence')

    parent = ProjectDetailsView
    url_fragment = "clauses"


    def get_form_kwargs(self):
        kwargs = super(ClauseView, self).get_form_kwargs()
        if self.request.method == 'GET' and 'sentence' in self.request.GET:
            kwargs['data'] = self.request.GET

        return kwargs

    def get(self, request, *args, **kwargs):
        if 'sentence' in self.request.GET:
            return super(ClauseView, self).post(request, *args, **kwargs)
        else:
            return super(ClauseView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        # Get parse
        sent = form.cleaned_data['sentence']
        parse = get_adhoc_result('clauses_en', sent)
        saf = SAF(parse)
        tokens  = saf._tokens

        # add codebook
        codebook_id = 3
        codebook = Codebook.objects.get(pk=codebook_id)
        saf.saf['codes'] = list(match_codes(saf, codebook))

        # get tokens and clauses
        tokens = saf.resolve()
        clauses = list(saf.get_reduced_clauses())

        # add frames
        for clause in clauses:
            add_frames(saf, clause)

        # provide list of all codes
        codes = set(flatten(t.get('codes', []) for t in tokens))

        # resolve all places in the clauses
        for clause in clauses:
            for place in ['source', 'subject', 'predicate']:
                clause[place] = saf.resolve(clause[place])
        print clauses
        # make tree
        from syntaxrules.syntaxtree import SyntaxTree, VIS_IGNORE_PROPERTIES
        import base64
        VIS_IGNORE_PROPERTIES.append("clause_role")
        VIS_IGNORE_PROPERTIES.append("clause_id")
        VIS_IGNORE_PROPERTIES.append("source_role")
        VIS_IGNORE_PROPERTIES.append("source_id")
        VIS_IGNORE_PROPERTIES.append("pos")

        t = SyntaxTree(saf.saf)
        g = t.get_graphviz()
        tree = base64.b64encode(g.draw(format='png', prog='dot'))

        ctx = dict(form=form,
                   clauses=clauses,
                   tokens=tokens,
                   saf=json.dumps(saf.saf, indent=2),
                   codes=codes,
                   tree=tree)

        return self.render_to_response(self.get_context_data(**ctx))


def get_frames(su, pr):
    if "israel" in su and "attack" in pr:
        yield "ISRAEL_MEANS"
    if "palestine" in su and "attack" in pr:
        yield "ISRAEL_PROBLEM"
    if "israel" in pr and "attack" in pr:
        yield "ISRAEL_PROBLEM"

def add_frames(saf, clause):
    su_codes = set(flatten(saf.get_token(t).get('codes', []) for t in clause['subject']))
    pr_codes = set(flatten(saf.get_token(t).get('codes', []) for t in clause['predicate']))
    frames=set(get_frames(su_codes, pr_codes))
    clause.update(dict(subject_codes=su_codes, predicate_codes=pr_codes, frames=frames))
