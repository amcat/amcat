from frames import *
from lexicon import *

########## RULE DEFINITIONS ###################

#Uit rule_bron_3_N:
#        frame=Bron(getMoetOrder(frame.quote,act),key=node,source=frame.source,quote=frame.quote,negation=frame.negation)
#        ok = 1
#    if not (isDat(frame.quote) or  getDescendant(getAncestor(node," --"),"sat") or ok) : return
#def rule_bron_7_voltooiddeelwoord(node):
#    #is verrast over ... moet eigenlijk worden opgevangen door SPO1?actief if not frame.object: frame.object = getChild(getChild(node, "pc"),"obj1") 
#    if not (node.word.lemma.pos=='A'  and getParent(node,"mod") and isVHulpww(getParent(node)) ): return
#    frame = SPO("spo",predicate=node)
#    frame.subject = getChild(getParent(node,"mod"),"su")
#    frame.object = getChild(getChild(node,"pc"),"obj1")
#    if not frame.object: frame.object = getChild(getParent(node,"mod"),"sat") 
#    return frame
#WvA: nut? 43764841 is ok? BronRule(i, N_SPEECH_ACTS, quote=Serial(Ancestor(pos="V"), Child("vc")), source=Pattern(nZegSource)),
#WvA nut? BronRule(i, N_SPEECH_ACTS, quote=Serial(Ancestor("--"), Descendant("sat")), source=Pattern(nZegSource)),
#WvA stonden nog opmerkingen:
#   dubieus of je isDat moet eisen, bv te stringent in Bos zei nee 39417441, daarom niet geeist als getChild "obj1"
#    if frame.quote: frame.name = getMoetOrder(frame.quote,act) (is dat voor 34555771?)
#WvA hier zat een eis (isVBelofte(node) or isVOrder(node)) aan vast, maar zie 34669402
#WvA: ???????? 39400763, uitbreidende isVzeg bijzin: Timmermans (mod) die (su) zei, had ook met getResolveSource gekund

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
        BronRule(i, V_PASSIVE_SPEECH_ACTS, postprocess=VPostProcess, source=Child("obj2"), quote=Child("su")), 
        BronRule(i, V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("tag")), #39397183
        BronRule(i, V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("dp")), #39404298
        BronRule(i, V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child("pc"),
                  checks=[Ancestor(rel="--"), Parent("dp")]), #    39397435
        BronRule(i, V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Parent("dp")), #39397365
        BronRule(i, V_SPEECH_ACTS, postprocess=VPostProcess, source=Child("su"), quote=Child(("vc", "obj1", "nucl"))),

        BronRule(i, N_SPEECH_ACTS, quote=Child("vc"), source=Pattern(nZegSource)), #34763507
        BronRule(i, N_SPEECH_ACTS, quote=Sibling("obj1", "dp"), source=Pattern(nZegSource)), #34763507

        BronRule(i, N_SPEECH_ACTS, quote=Serial(Parent("obj1"), Child("su")),
                 source=Serial(Parent("obj1"), Child("mod", pos="P"), Child("obj1"))), #31310 maar ook onterechte match hoofdww

        BronRule(i, VOLGENS_ACTS, source=Child("obj1"), quote=Serial(Parent(["mod", "tag"]), Root(pos="V"))), #39396066, 39396205,
        BronRule(i, VOLTOOID_ACTS, source=Child("obj1"), quote=Serial(Child("pc"), Child("vc"))), # zie  39397172
        BronRule(i, VOLTOOID_ACTS, source=Sibling("predc", "su"), quote=Serial(Child("pc"), Child("vc"))), # zie 38667309 

        # klopt 39417595 wel?
        BronRule(i, DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child(["nucl","sat"]))), #39417433
        BronRule(i, DIREDE_ACTS, source=Child("--"), quote=Serial(Child("--"), Child("dp", check=hassu))), #39397408

        # hoe 39397415 te vangen?frame.object = getChild(getChild(getChild(node, "mod"), "pc"),"obj1") #39397415 Van Bommel verrast
        
        DeclarativeRule(i, SPO, name="spo", condition=[isVNotZeg, isHighestV], postprocess=negation,
                        subject=Serial(childOfLowestV("su"), Pattern(resolveDie)),
                        object=FirstMatch(Serial(Child("obj2", pos="P"), Child("obj1")),
                                          Child("obj2"),
                                          Child("obj1"),
                                          Child("predc"),
                                          Serial(childOfLowestV("mod"), Child("obj1")),
                                          Serial(childOfLowestV("pc"), Child("obj1")),
                                          Serial(childOfLowestV("ld"), Child("obj1")),
                                          ),
                        predicate=Self()), # passief bij lowest(mod).lemma=door
        
    ]:
        i.rules.append(r)
    return i

def negation(identifier, frame):
    frame.negation = getChild(frame.predicate, "mod")
    return frame

def rule_spo_1actief(node):

    if not frame.object:
        #debug("xxxxxxxxxxxxxxxxxxx..............",getChild(node,"mod"))
        frame.object = getChild(getChild(getChild(node, "mod"), "pc"),"obj1") #39397415 Van Bommel verrast
    #if not frame.object and getDescendant(getChild(node, "vc"), "obj1"): frame.object = getChild(node, "vc")   
    if not frame.object: frame.object = getChild(getChild(node,"ld"),"obj1")
    #pdoel=getChild(frame.object, "mod") #om-constructie hangt aan object, zie 39403134
    #if not pdoel: pdoel = getChild(node, "mod")
    #if pdoel:
    #    if pdoel.word.lemma.label in ("met het oog op", "om","omwille","opdat","zodat","waardoor","teneinde","voor"):
    #        frame2 = getPurpose(node,pdoel,frame.subject) # 39404297
    #        return [frame, frame2]
    #    elif pdoel.word.lemma.label in ("met"):  #met als isGoal, 39405708
    #        pkey = isGoal(getDescendant(pdoel,pos="N"))
    if isNiet(getChild(node, "mod")): frame.negation = getChild(node, "mod")  
    doBijzinSODraai(frame)
    doelframe = getDoel(frame.object, frame.predicate) or getDoel(frame.predicate, frame.predicate)
    return [frame, doelframe]  
    
def childOfLowestV(*args, **kargs):
    return Serial(Lowest("vc"), Child(*args, **kargs))

def resolveDie(node):
    if node and node.word.lemma.label in ("die","dat","welke","dewelke"): #39400763, beperkende bijzin: Verhagen (mod) die (su) node
        return getParent(node, "mod")
    return node
    

class FirstMatch(object):
    def __init__(self, *rules):
        self.rules = rules
    def getNode(self, node):
        for rule in self.rules:
            n = rule.getNode(node)
            if n: return n

class Lowest(Conditional):
    def __init__(self, rel):
        self.rel = rel
    def getNode(self, node):
        lowest = node
        while getChild(lowest, self.rel):
            lowest = getChild(lowest, self.rel)
        return lowest


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
    return True
    

    
def VPostProcess(identifier, frame):
    mod = getChild(frame.key, "mod")
    if identifier.hasLemma(mod, NEGATORS): frame.negation= mod
    if identifier.hasLemma(mod, DOELWOORDEN): frame.goal = mod #34669402
    if frame.source and getParent(frame.source, "mod") and frame.source.word.lemma.label in ("die","dat","welke","dewelke"):
        frame.source = getParent(frame.source, "mod")
    if frame.source and identifier.hasLemma(frame.source, N_GEZEGDE_LEMMATA, 'N'): #39417595
        frame.source,frame.quote = frame.quote,frame.source
    return frame
