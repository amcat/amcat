from frames import *
from lexicon_en import *

##########RULE DEFINITIONS ###################

def false(*what, **ever): return False

V = Check(pos="v")

def isVNotZeg(identifier, node):
    #TODO: niet alleen zeg-lemmata
    pos = node.word.lemma.pos.lower()
    if pos<> "v":
        return False # getChild(node, "cop")
    for lemmata in (SAY_LEMMATA, ORDER_LEMMATA):
        if identifier.hasLemma(node, lemmata, "V"): return False
    return True

def isProposal(i, node):
    return i.hasLemma(node, PROPOSAL_LEMMATA, "N")

def isAttack(i, node):
    return i.hasLemma(node, ATTACK_LEMMATA, "N")

def isCopula(i, node):
    if not i.hasLemma(node, COPULA_LEMMATA, "V"): return False
    return getChild(node, "cop")

def isThereIs(i, node):
    if not isCopula(i, node): return False
    return getChild(node, "expl", lemma="there")

def allowPartialSPO(frame):
    # Determine whether an SPO frame is allowed to be incomplete or not
    if not frame.rule: return True # came from db
    if frame.rule.identifier.hasLemma(frame.predicate, SUCFAIL_LEMMATA, "V"): return True

def getIdentifier(db, debug=None):
    i = Identifier(db, debug=debug)
    for r in [
        BronRule(i, '1', V_SPEECH_ACTS,source=Child("nsubj"), quote=FirstMatch(Child(["dobj", "ccomp"]), Parent("dep"))),
        BronRule(i, 'ORD', V_ORDERS, source=Child("nsubj"), addressee=Child("dobj"), quote=Serial(Child("dobj"), Child("infmod"))),

        BronRule(i, 'acc', V_ACCORDING, source=Serial(Child("dep"), Child("pobj")), quote=Parent('prep')),
        
        #SPORule(i, "copula", predicate=Child("cop"), subject=Child("nsubj"), object=Self()),
        #SPORule(i, "dep#", subject=Parent("dep"), object=Child("dobj"), precheck=false),

        SPORule(i, "pass", object=FirstMatch(Child("nsubjpass"), Parent("partmod")), subject=FirstMatch(
                Serial(Child("prep", lemma="by"), Child("pobj")),
                ), precheck=isVNotZeg, allowPartial=True),

        SPORule(i, 'actief',
                precheck=isVNotZeg,
                subject=FirstMatch(
                  Child("nsubj"),
                  Conditional(childOfConjoinedV, "nsubj"),
                  Serial(Parent("xcomp"), Child("nsubj"))),#52886613
                object=FirstMatch(
                  #Serial(childOfLowestV("prep"), Child("pobj")),
                  UseXtoY(),#52886613
                  childOfLowestV("dobj"),
                ),
                aux = Parent("xcomp"),#52886613
                allowPartial=allowPartialSPO),

        
        #52878501
        SPORule(i, 'attack', precheck=isAttack, subject=Serial(Child("prep", lemma=["from"]),Child("pobj")),object=Serial(Child("prep", lemma=["on"]),Child("pobj")), allowPartial=True),
        
        SPORule(i, 'propose', precheck=isProposal, subject=Child("amod"), object=Serial(Child("prep", lemma="for"), Child("pobj"))),
        
        DeclarativeRule(i, Equal, rulename="_app", name="app", subject=Self(), object=Child("appos")),
        DeclarativeRule(i, Equal, rulename="cop", name="cop", object=Child("cop"), subject=Child("nsubj"), predicate=Self(), precheck=isCopula),

        DeclarativeRule(i, Reality, rulename="therebe", name="rea", predicate=Self(), object=Child("cop"), precheck=isThereIs),
        
    ]:
        i.rules.append(r)
    return i
              

class UseXtoY(Pattern):
    def getNode(self, rule, node):
        if not rule.identifier.hasLemma(node, USE_LEMMATA): return
        node = getChild(node, "dobj")
        if node: node=getChild(node, "infmod")
        return node
    
def childOfLowestV(*args, **kargs):
    return Child(*args, **kargs) #Serial(Lowest("aux", pos="v"), Child(*args, **kargs))

def childOfConjoinedV(node, *args, **kargs):
    node = getParent(node, "conj")
    while node:
        n2 = getChild(node, *args, **kargs)
        if n2: return n2
        node = getParent(node, "ccomp")
    
