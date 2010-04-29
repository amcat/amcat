import alpino, zoektermen, toolkit

_BR = "<br/>"
def debug(x):
    #toolkit.warn(x)
    #print "%s%s" % (x, _BR)
    pass



UNDEF = 0
MALE = 1
FEMALE = 2

SINGULAR = 1
PLURAL = 2

ANIMATE = 1
INANIMATE = 2

class AnaphoricPronoun(object):
    def __init__(self, label, gender, number, person=3, animate=True):
        self.label = label
        self.gender = gender
        self.number = number
        self.person = person
        self.animate = animate


_A = AnaphoricPronoun

ANAPHORA = {
    'haar' : _A('zij/sg', FEMALE, SINGULAR),
    'hun' : _A('zij/pl', UNDEF, PLURAL, 3, UNDEF),
    'hij' : _A('hij', MALE, SINGULAR),
#    'ik' : _A(UNDEF, SINGULAR, 1)
    }

ANAPHORA['zij'] = ((ANAPHORA['haar'], ANAPHORA['hun']))
ANAPHORA['ze'] = ANAPHORA['zij']
ANAPHORA['hem'] = ANAPHORA['hij']
ANAPHORA['zijn'] = ANAPHORA['hij']
ANAPHORA['ze'] = ANAPHORA['zij']
#ANAPHORA['me'] = ANAPHORA['ik']
#ANAPHORA['mij'] = ANAPHORA['ik']

class AnaphoricNP(object):
    def __init__(self, label, relation, uniquePerParty, clas=None, animate=1):
        self.label = label
        self.relation = relation
        self.unique = uniquePerParty
        self.gender = 0
        self.number = 1
        self.animate = animate
        self.clas = clas


NPANAPHORA = {
    'kamerlid' : AnaphoricNP('tk', 'http://www.content-analysis.org/vocabulary/ontologies/k06#partOfFraction', False),
    'lijsttrekker' : AnaphoricNP('lt', 'http://www.content-analysis.org/vocabulary/ontologies/k06#lijsttrekker', True),
    'fractievoorzitter' : AnaphoricNP('fv', 'http://www.content-analysis.org/vocabulary/ontologies/k06#fractionleader', True),
    'minister' : AnaphoricNP('min', 'http://www.content-analysis.org/vocabulary/ontologies/k06#leadsDept', False),
    'partij' : AnaphoricNP('par', None, False, clas='http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-partij', animate=2),
    }


class AnaphoricReference(object):
    def __init__(self, pronoun, node, recognizer, party=None):
        self.pronoun = pronoun
        self.node = node
        self.rec = recognizer
        self.db = self.rec.db                
        self.label = "[%s %s]" % (pronoun.label, node.wordid)
        self.party = party
        self.number = None

    def resolve(self):
        """
        Resolve a anaphoric reference
        """
        debug("<< Resolving %s" % (self.label))
        for c in self.candidates():
            if self.synfilter(c):
                ants = self.agreefilter(c)
                debug(ants)
                if ants:
                    debug("===> Resolved %s to %s" % (self.label, ",".join(c.label for c in ants)))
                    return ants
        debug("===X Could not resolve %s" % (self.label))
        return None

    def synfilter(self, cand):
        if cand.sentence <> self.node.sentence: return True
        ns = cand.sentence.findAllCoIndexed(self.node)
        cs = cand.sentence.findAllCoIndexed(cand)

        for n in ns:
            for c in cs:
                if c.parent == n.parent: # lapin & leass (1997) 2.1.1 condition 2
                    debug(".. Exclude %s: Pronoun is in argument domain" % c.getWordid())
                    return False
                if n.parent.cat == "pp" and n.parent.parent == c.parent: # l&l 1997 2.1.1 condition 3
                    debug(".. Exclude %s: Pronoun is in adjunct domain" % c.getWordid())
                    return False
                if c in alpino.children(n.parent): # l&l 1997 2.1.1 condition 4
                    debug(".. Exclude %s: Descendent of parent of pronoun" % c.getWordid())
                    return False
                # Skipping l&l 1997 2.1.1 condition 5: complex and unlikely?
                # Skipping l&l 1997 2.1.1 condition 6: subsumed by #4
        return True

    def agreefilter(self, cand):
        ant = self.rec.find([cand])
        debug("--? %s" % ",".join("%s:%s" % (a.label, zoektermen.gender(a)) for a in ant))
        nr = self.number and self.number or self.pronoun.number
        if not ant:
            # this might not be smart
            debug(".. Exclude %s: Antecedent not recognized" % cand)
            return None
        if len(ant) > 1:
            debug("len(a)=%s and Pronoun number: %s" % (len(ant), self.pronoun.number))
            if self.pronoun.number == 1:
                debug(".. Exclude %s: pronoun is singular and antecedent plural" % cand)
                return None
        else:
            debug("Pronoun number: %s" % self.pronoun.number)
            if self.pronoun.number == 2:
                debug(".. Exclude %s: pronoun is plural and antecedent singular" % cand)
                return None
            a = list(ant)[0]
            g = zoektermen.gender(a)
            p = zoektermen.party(a)
            animate = not not p
            #debug("Ge/Par of %s: %s / %s" % (a, g, p))
            if (self.pronoun.animate == ANIMATE and not animate) or (self.pronoun.animate == INANIMATE and animate):
                debug("Exclude %s: animate candidate for inanimate pronoun or vice versa" % cand)
                return None
            if (self.pronoun.gender == MALE and g == 'female') or (self.pronoun.gender == FEMALE and g == 'male'):
                debug("Exclude %s: gender of pronoun and antecedent do not match" % cand)
                return None
            if type(self.pronoun)==AnaphoricNP:
                rel = a.ontology.get(self.pronoun.relation)
                if rel and not a.getOutgoing(rel):
                    debug("Exclude %s: require %s" % (cand, rel))
                    return None
                cls = a.ontology.get(self.pronoun.clas)
                if cls and not cls in a.classes:
                    debug("Exclude %s: require %s" % (cand, cls))
                    return None
                
        return ant
        

    def candidates(self):
        for s in self.candidatesentences():
            debug(s.sentence)
            cands = set()
            def iscontained(n):
                for n2 in cands:
                    if n2 <> n and n in n2.children:#alpino.children(n2):
                        return True
            for n in alpino.nodes([s.top]):
                if n.sentence == self.node.sentence and (n.parent and n.parent.end or 9999) >= self.node.begin: continue
               #debug("Considering %s" % (n.word or n.id))
                if (n.cat in ('np', 'mwu')) or ((n.pos in ('noun', 'name')) and (n.rel in 'su' , 'obj1', 'obj2')):
                    cands.add(n)
            cands = [x for x in cands if not iscontained(x)]
            cands.sort(lambda x,y: cmp(x.begin, y.begin))
            for func in 'su' , 'obj1', 'obj2', None:
                for c in cands:
                    if c.rel == func or (c.rel not in ('su' , 'obj1', 'obj2') and func is None):
                        debug("Candidate %s/%s/%s" % (func, c.getWordid() or c.root, c.id))
                        yield c

    def candidatesentences(self):
        yield self.node.sentence
        sql = "select sentenceid from sentences where articleid=(select articleid from sentences where sentenceid=%(sid)i) and parnr=(select parnr from sentences where sentenceid=%(sid)i) and sentnr < (select sentnr from sentences where sentenceid=%(sid)i) and articleid <> 35416866 order by sentnr desc" % self.node.sentence.__dict__
        for sid, in self.db.doQuery(sql):
            sent = alpino.getParse(sid, self.db)
            yield sent



def getPersoonsvorm(node):
    """
    Helper function to return the primary finite verb
    that node is the subject of
    """
    if node.rel <> 'su':
        node = node.indexed()
        if node and node.rel == 'su':
            return getPersoonsvorm(node)
        return None

    for child in node.parent.children:
        if child.rel == 'hd':
            return child
    return None

def strlist(nodes):
    return "/".join(node.root or `node.id` for node in nodes)

class Identifier(object):
    def __init__(self, recognizer):
        self.rec = recognizer
        self.db = recognizer.db
        

    def npanaphora(self, nodelist):
        result = set()
        #debug('NP Ana in %s / %s' % (strlist(nodelist), strlist(alpino.nodes(nodelist))))

        for onode in nodelist:
          for node in alpino.nodes([onode]):
            node = node.indexed()
            #debug('NP Ana in %s' % (node and node.root))
            if node.root in NPANAPHORA:
                ana = NPANAPHORA[node.root]
                debug(ana.label)
                det, mod = None, set()
                for child in node.parent.children:
                    if child.pos == 'det': det = child
                    if child.rel == 'mod': mod.add(child)

                if det and det.root in ('de', 'het', 'die', 'deze'):
                    debug('--> possible NP anaphora %s %s' % (det.root, node.root))
                    party  = set()
                    debug('  modifiers: (%s)' % ",".join(x.root or str(x.id) for x in mod))
                    kos = self.rec.find(mod)
                    if kos:
                        partyclass= list(kos)[0].ontology.get('http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-partij')
                        for ko in kos:
                            if partyclass in ko.classes:
                                party.add(ko)
                    if len(party)==1:
                        party = list(party)[0]
                        if ana.unique:
                            debug(party.ontology.get(ana.relation))
                            res = party.getIncoming(party.ontology.get(ana.relation))
                            if res:
                                res = list(res)[0]
                                debug("==> resolve to (%s) : unique per party" % res.label)
                                result.add(res)
                            else:
                                debug("==X Cannot find %s of %s" % (ana.label, party.label))
                        else:
                            a = AnaphoricReference(ana, node, self.rec, party)
                            onode.indexed().anaphora = 'pron np %s' % ana.label
                            result |= a.resolve() or set()
                    else:
                        a = AnaphoricReference(ana, node, self.rec)
                        if node.word <> node.root and (node.word.endswith('n') or node.word.endswith('s')):
                            a.number = 2
                        onode.indexed().anaphora = 'pron np %s' % ana.label
                        result |= a.resolve() or set()
        return result        

    def pronanaphora(self, nodelist):
        result = set()
        for node in alpino.nodes(nodelist):
            if node.pos == 'pron' and node.word.lower() in ANAPHORA:
                as = ANAPHORA[node.word.lower()]
                if type(as) == tuple:
                    as = self._disambiguate(node, as)
                result.add(AnaphoricReference(as, node, self.rec))
                node.indexed().anaphora = 'pron %s' % as.label
                debug("Anaphora: %s<br/>"% (node.word or node.root or node.id))
        return result


    def _disambiguate(self, node, choices):
        """
        Disambiguate pronouns based on the number (pl or sg)
        of the finite verb, or select the first candidate
        """ 
        pv = getPersoonsvorm(node)
        #pos = pv and pv.getPostag(self.db)
        #if not pos: return list(choices)[0]
        
        #pos, info = pos.split("(", 1)
        #info = info.split(",")
        #number = info[1] == 'pl' and 2 or 1
        
        #debug("Number: %s (%s / %s)" % (number, pv and pv.root, info))

        number = pv and pv.word.endswith('n') and 2 or 1
        
        for choice in choices:
            if choice.number == number: return choice
        return list(choices)[0]


if __name__ == '__main__':
    import sys, dbtoolkit, pySesame2, ontology2
    _BR = ""
    sent = sys.argv[1]
    anaid = sys.argv[2]
    
    db = dbtoolkit.anokoDB()
    
    rdfdb = pySesame2.connect(database="anoko-test")
    ont = ontology2.fromPickle(rdfdb)

    objects = set()
    rel = ont.get('http://www.content-analysis.org/vocabulary/ontologies/k06#memberOfParty')
    for role in rel.instances:
        objects.add(role.object)
        objects.add(role.subject)
        
    import zoektermen
    rec = zoektermen.Recognizer(objects, db)
    
    parse = alpino.getParse(sent, db)
    ana = parse.findnodebywordid(anaid)

    if not ana: raise Exception("Cannot find anaphora %s in parse" % anaid)

    i = Identifier(rec)
    for ref in i.anaphora([ana]):
        print "Resolving %s" % ref.label
        ref.resolve()
    
    
    
