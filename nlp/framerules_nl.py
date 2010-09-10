from frames import *
from lexicon_nl import *

##########RULE DEFINITIONS ###################


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

#34755418 niet gevonden?

def getIdentifier(db, debug=None):
    i = Identifier(db, debug=debug)
    for r in [
        BronRule(i, '-1', V_PASSIVE_SPEECH_ACTS, postprocess=VPostProcess, source=Child("obj2"), quote=Child("su")), 
        BronRule(i, '_10', VOLGENS_ACTS, source=Child("obj1"), quote=Serial(Parent(["mod", "tag"]), Root(pos="V"))), #39396066, 39396205,
        BronRule(i, '_2', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("tag")), #39397183
        BronRule(i, '_3', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("dp")), #39404298
        BronRule(i, '_4', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("pc"),
                  checks=[Ancestor(rel="--"), Parent("dp")]), #    39397435
        BronRule(i, '_5', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("dp")), #39397365
        BronRule(i, '_6', V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child(("vc", "obj1", "nucl"))),

        BronRule(i, '_7', N_SPEECH_ACTS, quote=Child("vc"), source=Pattern(nZegSource)), #34763507
        BronRule(i, '_8', N_SPEECH_ACTS, quote=Sibling("obj1", "dp"), source=Pattern(nZegSource)), #34763507
        BronRule(i, '_15', N_SPEECH_ACTS, quote=Pattern(nZegQuote), source=Pattern(nZegSource)), #39397415
        BronRule(i, '_9', N_SPEECH_ACTS, quote=Serial(Parent("obj1"), Child("su")),
                 source=Serial(Parent("obj1"), Child("mod", pos="P"), Child("obj1"))), #31310 maar ook onterechte match hoofdww

        BronRule(i, '_11', VOLTOOID_ACTS, source=Child("obj1"), quote=Serial(Child("pc"), Child("vc"))), # zie  39397172
        BronRule(i, '_12', VOLTOOID_ACTS, source=Sibling("predc", "su"), quote=Serial(Child("pc"), Child("vc"))), # zie 38667309 

        # klopt 39417595 wel?
        BronRule(i, '_13', DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child(["nucl","sat"]))), #39417433
        BronRule(i, '_14', DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child("dp", check=hassu))), #39397408

        # hoe 39397415 te vangen?frame.object = getChild(getChild(getChild(node, "mod"), "pc"),"obj1") #39397415 Van Bommel verrast
        
 
        SPORule(i, 'passief', condition=[isVNotZeg, isHighestV], postprocess=draai,
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
     
 
 
        SPORule(i, 'actief', condition=[isVNotZeg, isHighestV], postprocess=draai,
                subject=Serial(childOfLowestV("su"), Pattern(resolveDie), Pattern(bijzin)), #actief
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
                                                                                                               
        DeclarativeRule(i, Goal, condition=[isDoelPredicate],                                                                                         
                        key = Self(),                                                                                                                 
                        doel = FirstMatch(Serial(Child("body"), Child("vc")),     #eigenlijk fout, dat er een vc is een hulpwerkwoord-test, body=hulpwerkwoord moet dan doel zijn
                                          Serial(Child("body"), Child("body"))),  #44499900 te-constructie
                        middel = Serial(Parent(["mod","vc"]), HighestV())),  
        DeclarativeRule(i, Goal, condition=[isMeansPredicate,notPassiveVoice],                                                                                         
                        key = Self(),                                                                                                                 
                        middel = FirstMatch(Serial(Child("body"), Child("vc")),     #eigenlijk fout, dat er een vc is een hulpwerkwoord-test, body=hulpwerkwoord moet dan doel zijn
                                            Serial(Child("body"), Child("body")),
                                            Child("obj1"),  #44499900 te-constructie
                                            Child("mod",pos="V")), #44501308 waartoe-constructie
                        doel = FirstMatch(Serial(Parent(["mod","vc"]),HighestV()),
                                          Serial(Parent("mod"),Parent("obj1"),HighestV()))),
        DeclarativeRule(i, Cause, condition=[isConsistent],                                                                                         
                        key = Self(),                                                                                                                 
                        dueTo = FirstMatch(Child("cnj"),Parent("mod")),
                        consequence = FirstMatch(Child("cnj"),Child("body")) ),
        DeclarativeRule(i, NegCause, condition=[isInconsistent],                                                                                         
                        key = Self(),                                                                                                                 
                        consequence = Parent("mod"),
                        despite = Child("body") ),
        DeclarativeRule(i, Assume, condition=[isPrecondition],                                                                                         
                        key = Self(),                                                                                                                 
                        consequence = FirstMatch(Parent("mod"), Parent("predm"), Child("nucl"),
                                          Serial(Parent("body"),Parent("mod")) ),   #44505248 dekt ook negative condities, uitgezonderd wanneer, behalve als
                        assumption = Child("body") ,
                       # conditionality = Child("mod", lemma="behalve")
                        ),                        
        DeclarativeRule(i, Succession, condition=[isTimelyOrder],                                                                                         
                        key = Self(),                                                                                                                 
                        consequence = Parent("mod"),
                        precedent = Child("body") ),
    ]:
        i.rules.append(r)
    return i
              
    
def isDoelPredicate(rule, frame):                                                                                                                     
    return rule.identifier.hasLemma(frame.key, ["met het oog op","om","omwille","opdat","zodat","waardoor","teneinde","voor"])   
def isMeansPredicate(rule, frame):  
    return rule.identifier.hasLemma(frame.key, ["door","door middel van","middels","via","waartoe","waarvoor"]) 
def notPassiveVoice(rule,frame):           # 39403129 voorkomt doel-middelconstructies als PassiveVoice
    if (Child("obj1") and Serial(Parent("mod",pos="V"), Child(["obj1","su"])) ): return False
    return True
def isConsistent(rule, frame):                                                                                                                     
    return rule.identifier.hasLemma(frame.key, ["omdat","aangezien","want","daar","doordat"])   
def isInconsistent(rule, frame):                                                                                                                     
    return rule.identifier.hasLemma(frame.key, ["maar","doch","echter","niettemin","desalniettemin","hoewel","ofschoon"])  
def isPrecondition(rule, frame):                                                                                                                     
    return rule.identifier.hasLemma(frame.key, ["als","indien","mits","tenzij","vermits","wanneer","zodra"])                               
def isTimelyOrder(rule, frame):                                                                                                                     
    return rule.identifier.hasLemma(frame.key, ["alvorens","daarna","daarvoor","erna","ervoor","nadat","na","nadien","sinds","sedert","terwijl","toen","totdat","voor","voordat","voordien","waarna"])


    
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
    return Serial(Lowest("vc", pos="V"), Child(*args, **kargs))
def childOfLowestVPassive(*args, **kargs):
    if Serial(childOfLowestV("mod", lemma="door", pos="P"), Child("obj1")):
        return Serial(Lowest("vc", pos="V"), Child(*args, **kargs))


def HighestV():
    return Highest("vc",pos="V")
        
def resolveDie(node):
    if node and node.word.lemma.label in ("die","dat","welke","dewelke"): #39400763, beperkende bijzin: Verhagen (mod) die (su) node
        return getParent(node, "mod")
    return node

def isHighestV(rule, frame):
    node = frame.predicate
    if getParent(node,"vc"): return False
    return True

def isVNotZeg(rule, frame):
    #TODO: niet alleen zeg-lemmata
    v = frame.predicate
    while v:
        rule.debug("CHECKING %s" % v)
        for lemmata in (ZEG_LEMMATA, BELOOF_LEMMATA):
            if rule.identifier.hasLemma(v, lemmata, "V"): return False
        v = getChild(v, "vc")
    return frame.predicate.word.lemma.pos == "V"
    

    
def VPostProcess(identifier, frame):
    #mod = getChild(frame.key, "mod")
    mods = [mod for (mod, rel) in frame.key.children if rel == "mod"]
    for mod in mods:
        if identifier.hasLemma(mod, NEGATORS): frame.negation= mod
        if identifier.hasLemma(mod, DOELWOORDEN): frame.goal = mod #34669402
    if frame.source and getParent(frame.source, "mod") and frame.source.word.lemma.label in ("die","dat","welke","dewelke"):
        frame.source = getParent(frame.source, "mod")
    if frame.source and identifier.hasLemma(frame.source, N_GEZEGDE_LEMMATA, 'N'): #39417595
        frame.source,frame.quote = frame.quote,frame.source
    return frame
