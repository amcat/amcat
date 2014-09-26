from saf import SAF
import json

from django.views.generic.edit import FormView
from django import forms

from navigator.views.projectview import ProjectViewMixin, HierarchicalViewMixin, BreadCrumbMixin
from navigator.views.project_views import ProjectDetailsView
from amcat.tools.amcatxtas import get_adhoc_result
from amcat.models import Codebook

def get_source(saf, predicate):
    "Return the source tokens (if any) of a source that contains the whole predicate"
    predicate = set(predicate)
    result = set()
    for source in saf.sources:
        if predicate.issubset(set(source['quote'])):
            result |= set(source['source'])
    return result

def contained_tokens(saf, predicate):
    "Return all tokens in predicates contained in this predicate (list of token ids)"
    result = set()
    predicate = set(predicate)
    for clause in saf.clauses:
        p2 = set(clause['predicate']) | set(clause['subject'])
        if p2 != predicate and p2.issubset(predicate):
            result |= p2
    return result

def get_reduced_clauses(saf):
    for clause in saf.clauses:
        clause = clause.copy()
        # remove contained tokens
        clause['source'] = get_source(saf, clause['predicate'])
        clause['predicate'] = [t for t in clause['predicate'] if t not in contained_tokens(saf, clause['predicate'])]
        # resolve tokens
        for place in "source", "subject", "predicate":
            clause[place] = [saf.get_token(c) for c in clause[place]]
            clause[place] = sorted(clause[place], key=lambda t:t['offset'])
        yield clause

class ClauseView(HierarchicalViewMixin,ProjectViewMixin, BreadCrumbMixin, FormView):
    class form_class(forms.Form):
        sentence = forms.CharField(label='Sentence', max_length=255)

    parent = ProjectDetailsView
    url_fragment = "clauses"

    def form_valid(self, form):
        # Get parse
        sent = form.cleaned_data['sentence']
        parse = get_adhoc_result('clauses_en', sent)
        saf = SAF(parse)
        tokens  = saf._tokens

        clauses = list(get_reduced_clauses(saf))

        # make list of tokens with role
        roles = {} # role per token
        for i, clause in enumerate(clauses):
            for place in "subject", "predicate":
                for token in clause[place]:
                    roles[token['id']] = (place, i)
        src_roles = {} # source role per token
        for i, source in enumerate(saf.sources):
            for place in "source", "quote":
                for token in source[place]:
                    src_roles[token] = (place, i)

        tokens = list(saf.get_tokens(1))
        for t in tokens:
            t['role'] = roles.get(t['id'])
            t['src_role'] = src_roles.get(t['id'])

       
        # add codebook
        codebook = Codebook.objects.get(pk=568)
        codebook_dict = {}
        for code in codebook.codes:
            concept = None
            lemmata = []
            for label in code.labels.all():
                if label.language.label == "en":
                    concept = label.label
                else:
                    lemmata += [x.strip() for x in label.label.split(",")]
            codebook_dict[concept] = lemmata

        # add codes
        for t in saf.get_tokens(1):
            tlemma = t['lemma'].lower()
            for code, lemmata in codebook_dict.iteritems():
                for lemma in lemmata:
                    lemma = lemma.lower()
                    if lemma == tlemma or (lemma.endswith("*") and tlemma.startswith(lemma[:-1])):
                        t['codes'] = t.get('codes', []) + [code]

        # add coreferences
        corefs = dict(get_coreferences(saf.coreferences) if 'coreferences' in saf.saf else [])
        coref_groups = {group: i+1 for  (i, group) in enumerate({tuple(v) for v in corefs.values()})}
        codes_per_group = {}
        for group, i in coref_groups.iteritems():
            for token in group:
                t = saf.get_token(token)
                t['coref'] = i
                print t
                for code in t.get('codes', []):
                    codes_per_group[i] = codes_per_group.get(i, set()) | {code}
                    
        for group, i in coref_groups.iteritems():
            if i in codes_per_group and len(codes_per_group[i]) == 1:
                code = list(codes_per_group[i])[0]
                for token in group:
                    saf.get_token(token)['codes'] = [code]
                
        # make tree
        from syntaxrules.syntaxtree import SyntaxTree, VIS_IGNORE_PROPERTIES
        import base64
        VIS_IGNORE_PROPERTIES.append("role")
        VIS_IGNORE_PROPERTIES.append("src_role")
        VIS_IGNORE_PROPERTIES.append("pos")

        t = SyntaxTree(saf.saf)
        g = t.get_graphviz()
        tree = base64.b64encode(g.draw(format='png', prog='dot'))

        codes = set()
        for t in tokens:
            for code in t.get('codes', []):
                codes.add(code)

        ctx = dict(form=form,
                   clauses=clauses,
                   tokens=tokens,
                   saf=json.dumps(saf.saf, indent=2),
                   codes=codes,
                   tree=tree)





        return self.render_to_response(self.get_context_data(**ctx))

def merge(lists):
    """
    Merge the lists so lists with overlap are joined together
    (i.e. [[1,2], [3,4], [2,5]] --> [[1,2,5], [3,4]])
    from: http://stackoverflow.com/a/9400562
    """
    newsets, sets = [set(lst) for lst in lists if lst], []
    while len(sets) != len(newsets):
        sets, newsets = newsets, []
        for aset in sets:
            for eachset in newsets:
                if not aset.isdisjoint(eachset):
                    eachset.update(aset)
                    break
            else:
                newsets.append(aset)
    return newsets


def get_coreferences(coreferences):
    """Decode the SAF coreferences as (node: coreferencing_nodes) pairs"""
    coref_groups = []
    for coref in coreferences:
        nodes = []
        for place in coref:
            nodes += place
            # take only the heads of each coref group
        coref_groups.append(nodes)
    for nodes in merge(coref_groups):
        for node in nodes:
            yield node, nodes 
