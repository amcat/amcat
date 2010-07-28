from frames import *
from lexicon_en import *

##########RULE DEFINITIONS ###################


def getIdentifier(db, debug=None):
    i = Identifier(db, debug=debug)
    for r in [
        BronRule(i, '1', V_SPEECH_ACTS,source=Child("nsubj"), quote=FirstMatch(Child(["dobj", "ccomp"]), Parent("dep"))),

        SPORule(i, "copula", predicate=Child("cop"), subject=Child("nsubj"), object=Self()),
        SPORule(i, "dep#", subject=Parent("dep"), object=Child("dobj")),

        SPORule(i, "pass", object=FirstMatch(Child("nsubjpass"), Parent("partmod")), subject=Serial(Child("prep", lemma="by"), Child("pobj"))),

        SPORule(i, 'actief', subject=Child("nsubj"), object=Child("dobj")),
        
    ]:
        i.rules.append(r)
    return i
              
    

def isVNotZeg(rule, frame):
    v = frame.predicate
    while v:
        rule.debug("CHECKING %s" % v)
        for lemmata in (SAY_LEMMATA, ):
            if rule.identifier.hasLemma(v, lemmata, "V"): return False
        v = getChild(v, "vc")
    return frame.predicate.word.lemma.pos == "V"
