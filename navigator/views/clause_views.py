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
        codebook = forms.CharField(label='Codebook id', required=False)

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
        if 'codebook' in self.request.GET:
            codebook = Codebook.objects.get(pk=int(self.request.GET['codebook']))
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


def get_frames(s, p):
    """
    >> * Israeli means (either of the patterns below)
>>x subject: israel, predicate: attack
>>x OR: predicate: attack AND palestine

>> * Israeli goals
>> subject: palestine, predicate: disarm OR (stop AND (attack or terror))

>> * Israeli moral evaluation:
>> subject: palestine, predicate: terror OR (attack AND citizens)
>> (optionally OR: predicate: israel AND (terror OR (attack AND cititzens))

>> * Israeli problem defition (mirror of israeli means)
>> subject: palestine, predicate: attack
>> OR: predicate: attack AND israel
    """

    if "terror" in p and palestine in (s|p):
        yield "ISRAEL_MORAL"

    if "stop" in p and "attack" in p and "palestine" in (s|p):
        yield "ISRAEL_GOAL"
        yield "ISRAEL_PROBLEM"

    if "attack" in p and "stop" not in p:
        if "israel" in s and not "palestine" in s:
            yield "ISRAEL_MEANS"
        if not "israel" in s and "palestine" in s:
            yield "ISRAEL_PROBLEM"
        if "israel" not in s and "palestine" not in s:
            if "israel" in p and not "palestine" in p:
                yield "ISRAEL_PROBLEM"
            if not "israel" in p and "palestine" in p:
                yield "ISRAEL_MEANS"

def add_frames(saf, clause):
    su_codes = set(flatten(saf.get_token(t).get('codes', []) for t in clause['subject']))
    pr_codes = set(flatten(saf.get_token(t).get('codes', []) for t in clause['predicate']))
    frames=set(get_frames(su_codes, pr_codes))
    clause.update(dict(subject_codes=su_codes, predicate_codes=pr_codes, frames=frames))
