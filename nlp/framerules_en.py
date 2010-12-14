from frames import *
from lexicon_en import *

ANALYSISID=4

##########RULE DEFINITIONS ###################

def false(*what, **ever): return False

V = Check(pos="v")

def isVNotZeg(rule, node):
    #TODO: niet alleen zeg-lemmata
    pos = node.word.lemma.pos.lower()
    if pos<> "v":
        return False # getChild(node, "cop")
    for lemmata in (SAY_LEMMATA, ORDER_LEMMATA):
        if rule.identifier.hasLemma(node, lemmata, "V"): return False
    return True

def isProposal(rule, node):
    return rule.identifier.hasLemma(node, PROPOSAL_LEMMATA, "N")

def isAttack(rule, node):
    return rule.identifier.hasLemma(node, ATTACK_LEMMATA, "N")
def isCalledVerb(rule, node):
    return rule.identifier.hasLemma(node, PAINT_LEMMATA, "V")

def isCopula(rule, node):
    if not rule.identifier.hasLemma(node, COPULA_LEMMATA, "V"): return False
    return getParent(node, "cop")

def isVictimOfN(rule, node):
    return (rule.identifier.hasLemma(node, COPULA_PREDICATE_NOUNS, "N") and
            not getChild(node, "cop"))

def copulaToPredicate(rule, frame):
    log.debug("copulaToPredicate(%s, %s)" % (rule, frame))
    if rule.identifier.hasLemma(frame.object, COPULA_PREDICATE_NOUNS, "N"):
        of = getChild(frame.object, "prep", lemma="of")
        rule.debug("of=%s" % of)
        if of:
            obj = getChild(of, "pobj")
            rule.debug("obj=%s" % obj)
            if obj:
                rule.debug("returning %s" % SPO(rule, obj, frame.object, frame.subject))
                return SPO(rule, obj, frame.object, frame.subject)
    rule.debug("returning %s" % frame)
    return frame

def isThereIs(rule, node):
    if not isCopula(rule, node): return False
    return getChild(node, "expl", lemma="there")

def haswho(rule, frame):
    return getChild(frame.predicate, "rel", lemma="who")




def allowPartialSPO(frame):
    # Determine whether an SPO frame is allowed to be incomplete or not
    if not frame.rule: return True # came from db
    if frame.rule.identifier.hasLemma(frame.predicate, SUCFAIL_LEMMATA, "V"): return True


def getIdentifier(db, *rulesets):
    if not rulesets: rulesets = [ALLRULES]
    i = Identifier(db, ANALYSISID)
    for ruleset in rulesets:
        for rule in ruleset:
            rule.identifier = i
            i.rules.append(rule)
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
    



ALLRULES = [
        BronRule('1', V_SPEECH_ACTS,source=Child("nsubj"), quote=FirstMatch(Child("ccomp"), Child("dobj"), Parent("dep"))),
        BronRule('ORD', V_ORDERS, source=Child("nsubj"), addressee=Child("dobj"), quote=Serial(Child("dobj"), Child("infmod"))),

        BronRule('acc', V_ACCORDING, source=Serial(Child("dep"), Child("pobj")), quote=Parent('prep')),

        BronRule('ing', V_SPEECH_ACTS, source=Serial(Parent("xcomp"), Child("nsubj")), quote=Child('ccomp')),

 
        # X present [Y as Z]  #52959677
        DeclarativeRule(Equal, rulename="iscalled", name="iscalled", precheck=isCalledVerb,
                        subject=Child("dobj"), object=Serial(Child("dobj"), Child("prep", lemma="as"), Child("pobj")),
                        predicate=Self(), source=FirstMatch(Child("nsubj"),
                                   Serial(Parent("infmod"), Child("prep",lemma="by"), Child('pobj')))),

        
        #SPORule("copula", predicate=Child("cop"), subject=Child("nsubj"), object=Self()),
        #SPORule("dep#", subject=Parent("dep"), object=Child("dobj"), precheck=false),

        SPORule("pass", object=FirstMatch(Child("nsubjpass"), Parent("partmod")), subject=FirstMatch(
                Serial(Child("prep", lemma="by"), Child("pobj")),
                ), precheck=isVNotZeg, allowPartial=True),

        SPORule('actief',
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
        SPORule('attack', precheck=isAttack,
                subject=FirstMatch(Serial(Child("prep", lemma=["from"]),Child("pobj")),
                                   Child("poss")),
                object=Serial(Child("prep", lemma=["on","towards"]),Child("pobj")),
                allowPartial=True),
        
        SPORule('propose', precheck=isProposal, subject=Child("amod"), object=Serial(Child("prep", lemma="for"), Child("pobj"))),


        
        DeclarativeRule(Equal, rulename="_app", name="app", subject=Self(), object=Child("appos")),
        DeclarativeRule(Equal, rulename="cop", name="cop", object=Parent("cop"),
                        subject=FirstMatch(Serial(Parent("cop"), Child("nsubj")),
                                           Serial(Parent("cop"), Parent("xcomp"), Child("nsubj"))),
                        predicate=Self(), precheck=isCopula, postprocess=copulaToPredicate),

        # X who are the Y #52869558
        #DeclarativeRule(Equal, rulename="cop2", name="cop2", object=Child("cop"), subject=Parent("rcmod"), predicate=Self(), precheck=isCopula, condition=haswho),
        DeclarativeRule(Equal, rulename="cop2", name="cop2",
                        precheck=isCopula, condition=haswho,
                        object=Parent("cop"),
                        subject=Serial(Parent("cop"), Parent("rcmod")),
                        predicate=Self(),
                        postprocess=copulaToPredicate,
                        ),

        DeclarativeRule(Reality, rulename="therebe", name="rea", predicate=Self(), object=Child("cop"), precheck=isThereIs),


        #52963450  victim of Iraeli aggression without saying whom
        SPORule('victimof',
                precheck=isVictimOfN,
                subject=Serial(Child("prep",lemma="of"), Child("pobj")),
                predicate=Self(),
                allowPartial=True)
                
    ]
              

#import amcatlogging; amcatlogging.debugModule()
