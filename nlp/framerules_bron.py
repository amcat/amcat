from frames import *
from lexicon_nl import *

ANALYSISID=2

##########RULE DEFINITIONS ###################

def isPrecondition(rule, node):                                                                                                                     
    return rule.identifier.hasLemma(node, ["als","indien","mits","tenzij","vermits","wanneer","zodra"])

def childOfLowestV(*args, **kargs):
    return Serial(Lowest("vc", pos="V"), Child(*args, **kargs))
def childOfLowestVPassive(*args, **kargs):
    if Serial(childOfLowestV("mod", lemma="door", pos="P"), Child("obj1")):
        return Serial(Lowest("vc", pos="V"), Child(*args, **kargs))


def nZegSource(node):
    det = getChild(node, "det")
    if det and det.word.label not in DETERMINERS: return det
    return (getChild(getChild(node, "mod", word="van"), "obj1") # de stelling van jan dat ..
            or getChild(getAncestor(node, pos="V"), "su")       # jan poneert de stelling dat
            or getChild(getParent(node, "obj1", pos='V'), "su"))           # jan heeft de mening dat .....

def hassu(node):
    return getChild(node, "su")

def nZegQuote(node):
    return (getChild(getAncestor(node, pos="V"), "su",word=["dat","of"])
            or getChild(getAncestor(node, pos="V"), "sat",word=["dat","of"]))

    
def bijzin(node):
    if node.word.lemma.label in ["die", "dat"]: 
        m = getParent(node, "mod")
        if m: return m
    return node


def resolveDie(node):
    if node and node.word.lemma.label in ("die","dat","welke","dewelke"): #39400763, beperkende bijzin: Verhagen (mod) die (su) node
        return getParent(node, "mod")
    return node

def draai(rule, frame):
    p = frame.predicate
    if p.word.lemma.pos == "V" and rule.identifier.hasLemma(p, V_DRAAI):        
        frame.subject, frame.object = frame.object, frame.subject
    return frame

def isHighestV(rule, node):
    if getParent(node,"vc"): return False
    return True

def isHighestV(rule, node):
    p = getParent(node, "vc")
    return (not p)

def isVNotZeg(rule, node):
    if node.word.lemma.pos != "V": return False
    return True
    #TODO: niet alleen zeg-lemmata
    v = node
    while v:
        log.debug("CHECKING %s" % v)
        for lemmata in (ZEG_LEMMATA, BELOOF_LEMMATA):
            if rule.identifier.hasLemma(v, lemmata, "V"): return False
        v = getChild(v, "vc")
   
def VPostProcess(rule, frame):
    #mod = getChild(frame.key, "mod")
    mods = [mod for (mod, rel) in frame.key.children if rel == "mod"]
    for mod in mods:
        if rule.identifier.hasLemma(mod, NEGATORS): frame.negation= mod
        if rule.identifier.hasLemma(mod, DOELWOORDEN): frame.goal = mod #34669402
    if frame.source and getParent(frame.source, "mod") and frame.source.word.lemma.label in ("die","dat","welke","dewelke"):
        frame.source = getParent(frame.source, "mod")
    if frame.source and rule.identifier.hasLemma(frame.source, N_GEZEGDE_LEMMATA, 'N'): #39417595
        frame.source,frame.quote = frame.quote,frame.source
    return frame
 
def isTimelyOrder(rule, frame):                                                                                                                     
    return rule.identifier.hasLemma(frame.key, ["alvorens","daarna","daarvoor","erna","ervoor","nadat","na","nadien","sinds","sedert","terwijl","toen","totdat","voor","voordat","voordien","waarna"])

def isTIJD(rule, node):
    return rule.identifier.hasLemma (node, TIJD)

BRONRULES = [
        BronRule('-1', V_PASSIVE_SPEECH_ACTS, postprocess=VPostProcess, source=Child("obj2"), quote=Child("su")), 
        BronRule('_10', VOLGENS_ACTS, source=Child("obj1"), quote=Serial(Parent(["mod", "tag"]), Root(pos="V"))), #39396066, 39396205,
        BronRule('_2', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("tag")), #39397183
        BronRule('_3', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("dp")), #39404298
        BronRule('_4', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("pc"),
                  checks=[Ancestor(rel="--"), Parent("dp")]), #    39397435
        BronRule('_5', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("dp")), #39397365
        BronRule('_6', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child(("vc", "obj1", "nucl"))),

        BronRule('_7', N_SPEECH_ACTS, quote=Child("vc"), source=Pattern(nZegSource)), #34763507
        BronRule('_8', N_SPEECH_ACTS, quote=Sibling("obj1", "dp"), source=Pattern(nZegSource)), #34763507
        BronRule('_15', N_SPEECH_ACTS, quote=Pattern(nZegQuote), source=Pattern(nZegSource)), #39397415
        BronRule('_9', N_SPEECH_ACTS, quote=Serial(Parent("obj1"), Child("su")),
                 source=Serial(Parent("obj1"), Child("mod", pos="P"), Child("obj1"))), #31310 maar ook onterechte match hoofdww

        BronRule('_11', VOLTOOID_ACTS, source=Child("obj1"), quote=Serial(Child("pc"), Child("vc"))), # zie  39397172
        BronRule('_12', VOLTOOID_ACTS, source=Sibling("predc", "su"), quote=Serial(Child("pc"), Child("vc"))), # zie 38667309 

        # klopt 39417595 wel?
        BronRule('_13', DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child(["nucl","sat"]))), #39417433
        BronRule('_14', DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child("dp", check=hassu))), #39397408

        # hoe 39397415 te vangen?frame.object = getChild(getChild(getChild(node, "mod"), "pc"),"obj1") #39397415 Van Bommel verrast

        BronRule('_16', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Serial (Child(("vc", "obj1", "nucl")), Child ("body"))), 
       ]
        
SPORULES = [

 SPORule('passief', precheck=[isVNotZeg, isHighestV], postprocess=draai,
                 subject=FirstMatch(Serial(childOfLowestV("mod", lemma=["door","bij"], pos="P"), Child("obj1")),  #passief
                                    Serial(childOfLowestV("predc"),Child("mod", lemma=["door","bij"], pos="P"), Child("obj1")), #44501304
                                   ), #passief
                 object=Serial(FirstMatch(childOfLowestVPassive("su"),  #passief 39403127
                                          childOfLowestV("obj1"), #passief 44499664 welke eerst?
                                          ),
                               Pattern(bijzin)),
                 negation
                = Child("mod", lemma=NEGATORS),
                 ),  #probleem:  passief SPOrule mag geen halve spo_su en spo_obj kernzinnen afleveren! --> opgelost door SPO.isComplete
 
    
    SPORule('actief', precheck=[isHighestV, isVNotZeg], postprocess=draai,
            #subject=childOfLowestV("su"),
            subject=Child("su"),
            object=Serial(FirstMatch(Serial(Child("obj2", pos="P"), Child("obj1")),
                                         childOfLowestV("obj2"),   #meewerkend voorwerp zonder aan of voor      
                                         Serial(childOfLowestV("mod",word=["aan","voor"]), Child("obj1")), #39405696 geld uitlenen aan BANK, meewerkend voorwerpconstructie
                                         childOfLowestV("obj1"), #passief 44499664 welke eerst?
                                         Serial(childOfLowestV("pc"), Child("obj1")),   # 32777
                                         Serial(childOfLowestV("predc"),Child("pc"),Child("obj1")),   #44499676
                                         Serial(childOfLowestV("mod"), Child("obj1")), #39405696 welke eerst?
                                         Serial(childOfLowestV("mod"), Child("pc"), Child("obj1")),
                                         Serial(childOfLowestV("ld"), Child("obj1")),
                                         Child("predc")
                                         ),
                              Pattern(bijzin)),
                negation = Child("mod", lemma=NEGATORS),
                ),
    ]

ALLRULES =BRONRULES + SPORULES 
#ALLRULES =SPORULES 

# ALLRULES = DISCOURSERULES

def getIdentifier(db, *rulesets):
    if not rulesets: rulesets = [ALLRULES]
    i = Identifier(db, ANALYSISID)
    for ruleset in rulesets:
        for rule in ruleset:
            rule.identifier = i
            i.rules.append(rule)
    return i


#import amcatlogging; amcatlogging.debugModule()


