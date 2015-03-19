class SAF(object):
    def __init__(self, saf):
        self.saf = saf
        self._tokens = {t['id']: t for t in saf['tokens']}

    def get_token(self, token_id):
        return self._tokens[token_id]

    def get_children(self, token):
        if not isinstance(token, int): token = token['id']
        return ((rel['relation'], self.get_token(rel['child']))
                for rel in self.saf['dependencies'] if rel['parent'] == token)

    def __getattr__(self, attr):
        try:
            return self.saf[attr]
        except KeyError:
            return object.__getattribute__(self, attr)

    def get_tokens(self, sentence=None):
        """Return the tokens in this article or sentence ordered by sentence and offset"""
        tokens = self.saf['tokens']
        if sentence is not None:
            tokens = [t for t in tokens if t['sentence'] == sentence]
        return sorted(tokens, key = lambda t: (int(t['sentence']), int(t['offset'])))

    def resolve(self, ids=None):
        """
        Resolve the given token ids (or the whole article) to dictionaries
        Will contain token information (lemma, pos) and additional information
        such as codes, coreference, etc. if available
        """
        # get token dicts for given ids (or whole article)
        if ids is not None:
            tokens = (self.get_token(id) for id in ids)
        else:
            tokens = self.tokens
        tokens = sorted(tokens, key = lambda t: (int(t['sentence']), int(t['offset'])))

        # get coreferences (if available)
        if 'coreferences' in self.saf:
            corefs = dict(self.get_coreferences())
            coref_groups = {group: i+1 for (i, group) in enumerate(map(tuple, corefs.values()))}
            for token in tokens:
                if token['id'] in corefs:
                    token['coref'] = coref_groups[tuple(corefs[token['id']])]

        # get codes (if available)
        if 'codes' in self.saf:
            for code in self.codes:
                token = self.get_token(code['token'])
                token['codes'] = tuple(set(token.get('codes', ()) + (code['code'],)))

        # add sources (if available)
        if 'sources' in self.saf:
            src_roles = {} # source role per token
            for i, source in enumerate(self.sources):
                for place in "source", "quote":
                    for token in source[place]:
                        src_roles[token] = (place, i)
            for token in tokens:
                if token['id'] in src_roles:
                    token['source_role'], token['source_id'] = src_roles[token['id']]

        # add clauses (if available)
        if 'clauses' in self.saf:
            roles = {} # role per token
            for i, clause in enumerate(self.get_reduced_clauses()):
                for place in "subject", "predicate":
                    for token in clause[place]:
                        roles[token] = (place, i)
            for token in tokens:
                if token['id'] in roles:
                    token['clause_role'], token['clause_id'] = roles[token['id']]


        return tokens

    def get_source(self, tokenids):
        "Return the source tokens (if any) of a source that contains all tokens"
        for source in self.sources:
            if set(tokenids).issubset(set(source['quote'])):
                for token in source['source']:
                    yield token


    def get_reduced_clauses(self):
        "Reduce the clauses in saf by removing nested clauses and adding the source"
        def contained_tokens(predicate):
            for clause in self.clauses:
                p2 = set(clause['predicate']) | set(clause['subject'])
                if p2 != set(predicate) and p2.issubset(predicate):
                    for t in p2:
                        yield t
            for source in self.sources:
                # exclude sources from predicates
                if set(source['source']).issubset(set(predicate)):
                    for t in source['source']:
                        yield t
        for clause in self.clauses:
            clause = clause.copy()
            contained = set(contained_tokens(clause['predicate']))
            clause['predicate'] = [t for t in clause['predicate'] if t not in contained]
            if 'sources' in self.saf:
                clause['source'] = list(set(self.get_source(clause['predicate'])))

            yield clause


    def get_root(self, sentence):
        parents = {d['child'] : d['parent'] for d in self.saf['dependencies']
                   if self.get_token(d['child'])['sentence'] == sentence}
        # root is a parent that has no parents
        roots = set(parents.values()) - set(parents.keys())
        if len(roots) != 1:
            raise ValueError("Sentence {sentence} has roots {roots}".format(**locals()))
        return self.get_token(list(roots)[0])

    def get_sentences(self):
        return sorted({t['sentence'] for t in self.saf['tokens']})

    def get_node_depths(self, sentence):
        # return a dict with the dept of each node
        rels = [d for d in self.saf['dependencies']
            if self.get_token(d['child'])['sentence'] == sentence]
        generations = {self.get_root(sentence)['id'] : 0}
        changed = True
        while changed:
            changed = False
            for rel in rels:
                if rel['child'] not in generations and rel['parent'] in generations:
                    generations[rel['child']] = generations[rel['parent']] + 1
                    changed = True
        return generations

    def get_descendants(self, node, exclude=None):
        """
        Yield all descendants (including the node itself),
        stops when a node in exclude is reached
        @param exlude: a set of nodes to exclude
        """
        if isinstance(node, int): node = self.get_token(node)
        if exclude is None: exclude = set()
        if node['id'] in exclude: return
        exclude.add(node['id'])
        yield node
        for _rel, child in self.get_children(node):
            for descendant in self.get_descendants(child, exclude):
                yield descendant




    def get_coreferences(self):
        """Decode the SAF coreferences as (node: coreferencing_nodes) pairs"""

        def _merge(lists):
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

        coref_groups = []
        for coref in self.saf.get('coreferences', []):
            nodes = []
            for place in coref:
                nodes += place
            coref_groups.append(nodes)
        for nodes in _merge(coref_groups):
            for node in nodes:
                yield node, nodes
