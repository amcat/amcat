"""
Functions for dealing with saf 'clauses'

A clause is a construct with subject and predicate node ids

WvA Maybe this should just be placed in saf?
"""

import collections



def match_codes(saf, codebook, label_language='en'):
    """
    Return a list of {'token': 1, 'code': 'x'} dicts
    All non-label entries in the codebook will be used to match
    """
    codebook_dict = {} # label : lemmata
    for code in codebook.codes:
        concept = None
        lemmata = []
        for label in code.labels.all():
            if label.language.label == "en":
                concept = label.label
            else:
                lemmata += [x.strip() for x in label.label.split(",")]
        codebook_dict[concept] = lemmata

    # match codes
    codes_per_token = collections.defaultdict(set)
    for t in saf.get_tokens():
        tlemma = t['lemma'].lower()
        for code, lemmata in codebook_dict.iteritems():
            for lemma in lemmata:
                lemma = lemma.lower()
                if lemma == tlemma or (lemma.endswith("*") and tlemma.startswith(lemma[:-1])):
                    codes_per_token[t['id']].add(code)

    # add coreferences
    if 'coreferences' in saf.saf:
        corefs = dict(saf.get_coreferences())
        coref_groups = {group: i+1 for  (i, group) in enumerate({tuple(v) for v in corefs.values()})}
        codes_per_group = {} # group : codes
        for group, i in coref_groups.iteritems():
            for token in group:
                for code in codes_per_token[token]:
                    codes_per_group[i] = codes_per_group.get(i, set()) | {code}

        for group, i in coref_groups.iteritems():
            # only use unambiguous references, i.e. a single code
            if i in codes_per_group and len(codes_per_group[i]) == 1:
                code = list(codes_per_group[i])[0]
                for token in group:
                    codes_per_token[token].add(code)

    for token, codes in codes_per_token.iteritems():
        for code in codes:
            yield {'token': token, 'code': code}
