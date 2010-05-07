from frames import *
from lexicon import *

########## RULE DEFINITIONS ###################


def nZegSource(node):
    det = getChild(node, "det")
    if det and det.word.label not in DETERMINERS: return det
    return (getChild(getChild(node, "mod", word="van"), "obj1") # de stelling van jan dat ..
            or getChild(getAncestor(node, pos="V"), "su"))      # jan poneert de stelling dat ...
def hassu(node):
    return getChild(node, "su")



#34755418 niet gevonden?

def getIdentifier(db, debug=None):
    i = Identifier(db, debug=debug)
    for r in [
        BronRule(i, '_1', V_PASSIVE_SPEECH_ACTS, postprocess=VPostProcess, source=Child("obj2"), quote=Child("su")), 
        BronRule(i, '_2', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("tag")), #39397183
        BronRule(i, '_3', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("dp")), #39404298
        BronRule(i, '_4', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("pc"),
                  checks=[Ancestor(rel="--"), Parent("dp")]), #    39397435
        BronRule(i, '_5', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("dp")), #39397365
        BronRule(i, '_6', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child(("vc", "obj1", "nucl"))),

        BronRule(i, '_7', N_SPEECH_ACTS, quote=Child("vc"), source=Pattern(nZegSource)), #34763507
        BronRule(i, '_8', N_SPEECH_ACTS, quote=Sibling("obj1", "dp"), source=Pattern(nZegSource)), #34763507

        BronRule(i, '_9', N_SPEECH_ACTS, quote=Serial(Parent("obj1"), Child("su")),
                 source=Serial(Parent("obj1"), Child("mod", pos="P"), Child("obj1"))), #31310 maar ook onterechte match hoofdww

        BronRule(i, '_10', VOLGENS_ACTS, source=Child("obj1"), quote=Serial(Parent(["mod", "tag"]), Root(pos="V"))), #39396066, 39396205,
        BronRule(i, '_11', VOLTOOID_ACTS, source=Child("obj1"), quote=Serial(Child("pc"), Child("vc"))), # zie  39397172
        BronRule(i, '_12', VOLTOOID_ACTS, source=Sibling("predc", "su"), quote=Serial(Child("pc"), Child("vc"))), # zie 38667309 

        # klopt 39417595 wel?
        BronRule(i, '_13', DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child(["nucl","sat"]))), #39417433
        BronRule(i, '_14', DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child("dp", check=hassu))), #39397408

        # hoe 39397415 te vangen?frame.object = getChild(getChild(getChild(node, "mod"), "pc"),"obj1") #39397415 Van Bommel verrast
        
        SPORule(i, 'general', condition=[isVNotZeg, isHighestV], postprocess=draai,
                subject=FirstMatch(Serial(childOfLowestV("su"), Pattern(resolveDie), Pattern(bijzin)),
                                   Serial(childOfLowestV("mod", lemma="door", pos="P"), Child("obj1"))),
                object=Serial(FirstMatch(Serial(Child("obj2", pos="P"), Child("obj1")),
                                         Child("obj2"),
                                         childOfLowestV("obj1"),
                                         Child("predc"),
                                         Serial(childOfLowestV("mod"), Child("obj1")),
                                         Serial(childOfLowestV("mod"), Child("pc"), Child("obj1")),
                                         Serial(childOfLowestV("pc"), Child("obj1")),
                                         Serial(childOfLowestV("ld"), Child("obj1")),
                                         ),
                              Pattern(bijzin)),
                negation = Child("mod", lemma=NEGATORS),
                ),
        SPORule(i, 'passive', condition=[isVNotZeg], 
                subject=Serial(Child("mod", pos="P"), Child("obj1")),
                object=Child("obj1")) # passief (geen check op lemma='door'?)
        
    ]:
        i.rules.append(r)
    return i

def bijzin(node):
    if node.word.lemma.label in ["die", "dat"]: 
        m = getParent(node, "mod")
        if m: return m
    return node

def draai(identifier, frame):
    p = frame.predicate
    if p.word.lemma.pos == "V" and identifier.hasLemma(p, V_DRAAI):        
        frame.subject, frame.object = frame.object, frame.subject
    return frame

def childOfLowestV(*args, **kargs):
    return Serial(Lowest("vc"), Child(*args, **kargs))

def resolveDie(node):
    if node and node.word.lemma.label in ("die","dat","welke","dewelke"): #39400763, beperkende bijzin: Verhagen (mod) die (su) node
        return getParent(node, "mod")
    return node

def isHighestV(rule, frame):
    node = frame.predicate
    su = getChild(node, "su")
    if su and getChild(getParent(node,"vc"), "su") == su: return False
    return True
    
def isVNotZeg(rule, frame):
    for pos, acts in (V_PASSIVE_SPEECH_ACTS, V_SPEECH_ACTS):
        for lemmata in acts.values():
            if rule.identifier.hasLemma(frame.predicate, lemmata, pos):
                return False
    return frame.predicate.word.lemma.pos == "V"
    

    
def VPostProcess(identifier, frame):
    mod = getChild(frame.key, "mod")
    if identifier.hasLemma(mod, NEGATORS): frame.negation= mod
    if identifier.hasLemma(mod, DOELWOORDEN): frame.goal = mod #34669402
    if frame.source and getParent(frame.source, "mod") and frame.source.word.lemma.label in ("die","dat","welke","dewelke"):
        frame.source = getParent(frame.source, "mod")
    if frame.source and identifier.hasLemma(frame.source, N_GEZEGDE_LEMMATA, 'N'): #39417595
        frame.source,frame.quote = frame.quote,frame.source
    return frame
