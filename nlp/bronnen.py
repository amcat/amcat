from toolkit import Identity
import sys, parsetree

#TODO: flexibere selectie-opties op get*(), bv lemma/rel/pos
#TODO: makkelijker debuggen

################ Main rules #################
# All rules starting with rule_* will be
# traversed in alphabetical order
################

def rule_bron_6_directerede(node):
    if isVZeg(node): debug("kij.....")
    dubbelepunt = getParent(node," --")
    if dubbelepunt:
        if dubbelepunt.word.lemma.label in (" : "):   #39417433 
            frame=BronFrame("direde", key=dubbelepunt)
            frame.source = node
            frame.quote = getChild(node,"nucl") or getChild(node,"sat")
            debug ("xxxxx ",frame.key, frame.source, frame.quote)
            return frame


      
def rule_bron_2_V(node):
    if isVZeg(node) or isVPassief(node): act="zeg"
    elif isVOrder(node): act="order"
    elif isVVraag(node): act="vraag"
    elif isVBelofte(node): act="belofte"
    else: return
    frame = BronFrame(act, key=node)
    frame.negation=getChild(node, "mod", lemma="niet")

    if isVPassief(node): # passief: src=meewerkend vw., quote=subject
        frame.source = getChild(node, "obj2")
        frame.quote = getChild(node, "su")
    elif getParent(node,"tag"): # zie zin 39397183
        su = getChild(node, "su")
        q = getParent(node, "tag")
    elif getChild(node,"dp"):  #zinnen zonder , of : om citaat af te bakenen, 39404298 (zeg papa)
        frame.source = getChild(node,"su")
        frame.quote  = getChild(node,"dp")
        return frame
    elif getParent(node,"dp"):  #zinnen zonder , of : om citaat af te bakenen, 39397365 (zeg kind)
        frame.source = getChild(node,"su")
        frame.quote  = getParent(node,"dp")
        return frame
    else:
        frame.source = getChild(node, "su")
        frame.quote = getChild(node, ("vc","obj1","nucl"))
    if frame.source:   #39400763, uitbreidende isVzeg bijzin: Timmermans (mod) die (su) zei, had ook met getResolveSource gekund
        if frame.source.word.lemma.label in ("die","dat","welke","dewelke") and getParent(frame.source, "mod"):
            frame.source = getParent(frame.source, "mod")
#   dubieus of je isDat moet eisen, bv te stringent in Bos zei nee 39417441, daarom niet geeist als getChild "obj1"
    if isNGezegde(frame.source): #39417595
        frame.source,frame.quote = frame.quote,frame.source
    if not isDat(frame.quote) and getChild(node, ("vc","nucl")): return
    return frame


def rule_bron_3_N(node):
    if isNGezegde(node): act="zeg"
    elif isNVraag(node): act="vraag"
    elif isNBelofte(node): act="belofte"
    else: return
    frame = BronFrame(act, key=node)
    # determine quote:
    # (1) vc "stelling dat ...",
    # (2) obj1, dp (hoe alpino abuisieelijk te werk gaat bij stellinganme),
    # (3) V->vc (bv "zou de mening hebben dat")
    frame.quote = (getChild(node, "vc")
                   or getSibling(node, "obj1","dp") 
                   or getChild(getAncestor(node,pos="V"), "vc")) # stelling van jan

    det = getChild(node, "det")
    if isNotDeterminer(det):
        frame.source =det
    else:
        frame.source = (getChild(getChild(node, "mod", word="van"), "obj1") # de stelling van jan dat ..
                        or getChild(getAncestor(node, pos="V"), "su"))      # jan poneert de stelling dat ...
    if not isDat(frame.quote): return
    return frame

def rule_bron_4_volgens(node): # zie 39396066
    if not isVolgens(node): return
    frame = BronFrame("volgens", key=node)    
    frame.source = getChild(node, "obj1")
    frame.quote = (getParent(node, "mod")
                   or getParent(node, "tag"))
    rootverb = getRoot(frame.quote, pos='V') # zie 39396205
    if rootverb: frame.quote = rootverb
    return frame

def rule_bron_5_ervan(node): # zie 38667309
    if not isVoltooid(node): return
    frame = BronFrame("ervan", key=node)
    frame.source = (getChild(node, "obj1")
                    or getSibling(node, "predc", "su"))
    frame.quote = getChild(getChild(node, "pc"), "vc")
    return frame

def isVnotZeg(node):
    return (node.word.lemma.pos == 'V'
            and not (isVZeg(node) or isVPassief(node) or isVOrder(node) or isVVraag(node) or isVBelofte(node)))


def rule_SPO_1actief(node):
    # example subject/predicate/object function
    if not isVnotZeg(node): return
    frame = SPOFrame("spo", predicate=node)
    frame.subject = getSubjectResolveDie(node)

    obj2p = getChild(node, "obj2", pos="P")
    frame.object = getChild(obj2p, "obj1")
    if not frame.object: frame.object = getChild(node, "obj2") #object = MV
    if not frame.object: frame.object = getChild(getChild(node, "mod"),"obj1") #object=modMV 
    if not frame.object: frame.object = getChild(node, "obj1")
    if not frame.object: frame.object = getChild(node, "predc")
    #pdoel=getChild(frame.object, "mod") #om-constructie hangt aan object, zie 39403134
    #if not pdoel: pdoel = getChild(node, "mod")
    #if pdoel:
    #    if pdoel.word.lemma.label in ("met het oog op", "om","omwille","opdat","zodat","waardoor","teneinde","voor"):
    #        frame2 = getPurpose(node,pdoel,frame.subject) # 39404297
    #        return [frame, frame2]
    #    elif pdoel.word.lemma.label in ("met"):  #met als isGoal, 39405708
    #        pkey = isGoal(getDescendant(pdoel,pos="N"))
    doBijzinSODraai(frame)
    doelframe = getDoel(frame.object, frame.predicate) or getDoel(frame.predicate, frame.predicate)
    return [frame, doelframe]

def rule_SPO_2passiefdoor(node):
    if not isVnotZeg(node): return
    frame = SPOFrame("spo_door", predicate=node)
    hmod = getChild(node, rel="mod", pos="P")
    frame.subject = getChild(hmod,"obj1")
    frame.object  = getChild(node,"obj1")
    doBijzinSODraai(frame)
    return frame

#################### Hulpprocedures ########################dfasd

def getDoel(node, subject):
    frame = SPOFrame("purp", subject=subject)
    pdoel=getChild(node, "mod")
    if hasLemma(pdoel, ["met het oog op", "om","omwille","opdat","zodat","waardoor","teneinde","voor"]): #39404297
        frame.predicate = pdoel
        objecthook = pdoel
    elif hasLemma(pdoel, ["met"]):  #met als isGoal, 39405708
        doelkey = getDescendant(pdoel,pos="N")
        if not isGoal(doelkey): return
        frame.predicate = doelkey
        objecthook = getChild(pdoel, "vc")
    else: return
    frame.object = getDoelObject(objecthook)
    if not frame.isComplete(): frame = None
    return frame

def getDoelObject(pdoel):
    object = getChild(getChild(pdoel,"body"),"body")
    if not object: #met het oog op, met P, 39404297
        object = getChild(pdoel,"obj1")
        debug("1.......",pdoel,object)
    if not object: #zodat, met C, 39405692 
        object = getChild(getChild(pdoel,"body"),"vc")
        debug("2.......",pdoel,object)
    if not object: #zodat, met C, als geen werkwoord onder body, of werkwoord onder "te" 
        object = getChild(pdoel,"body")
        debug("3.......",pdoel,object)
    return object



def doBijzinSODraai(frame):
    frame.subject = getBijzin(frame.subject)
    frame.object = getBijzin(frame.object)
    if isSOdraai(frame.predicate):    #krijgen, ontvangen
        frame.subject, frame.object = frame.object, frame.subject

def getBijzin(node):
    if isBijzin(node): 
        m = getParent(node, "mod")
        if m: return m
    return node

def getSubjectResolveDie(node):
    subject = getChild(node, "su")
    if subject and subject.word.lemma.label in ("die","dat","welke","dewelke"): #39400763, beperkende bijzin: Verhagen (mod) die (su) node
        subject = getParent(subject, "mod")
    return subject

##################### Lexical definitions ########################

def isDat(node):
    return hasLemma(node, ["dat","of","te","wat","waardoor","waarom","waartoe","waarvoor"])

def hasLemma(node, lemmata):
    return node and node.word.lemma.label in lemmata

def isNGezegde(node):
    return hasLemma(node, ["aankondiging","aanwijzing","achtergrondinformatie","affirmatie","anekdote","argument","argumentatie","assertie","begripsbepaling","bekendmaking","bekentenis","belijdenis","beoordeling","bericht","bescheid","bevestiging","bevinding","beweegreden ","bewering","bewijsvoering","bezegeling","biecht","boodschap","communicatie","communis opinio","conclusie","consequentie","constatering","convictie","denkbeeld","dienstbericht","dienstmededeling","diepte-informatie","dispositie","droombeeld","drijfveer","eed","eindconclusie","eindindruk","eindmening","eindoordeel","erkentenis","expressie","geest","geheim","gelukstijding","gerucht","geste","getuigenis","gevoelen","gevolgtrekking","gezichtspunt","gimmick","herinnering","hoofdargument","hoofdconclusie","impuls","indicatie","indruk","info","informatie","inlichting","inside-informatie","intuitie","jobspost","jobstijding","kreet","legende","levensbiecht","lezing","mare","mededeling","melding","meineed","melding","mening","motivering","nieuws","nieuwstijding","nieuwtje","notificatie","observatie","ondervinden","oordeel","openbaarmaking","openbaring","opinie","opmerking","opstelling","opvatting","overtuiging","overweging","positie","predictie","proclamatie","profetie","punt","rede","reden","relaas","repliek","revelatie","schuldbekentenis","schuldbelijdenis","slogan","slotbepaling","slotconclusie","slotindruk","slotsom","soundbite","spoedboodschap","standpunt","staving","stelling","stellingname","stokpaardje","suggestie","tegenbericht","tijding","tip","topic","totaalindruk","treurmare","uitdrukking","uiting","uitspraak","verdediging","vergezicht","verhaal","verklaring","vertelling","vertolking","verwijzing","verwoording","verzekering","vingerwijzing","visie","volksovertuiging","voorspelling","voorstellingswijze","waarneming","weerwoord","wending","wereldopinie","woord","zienswijze","zinsnede","zinsuiting","abstractie","axioma","bedenksel","beginsel","benul","bewijs","bijgedachte","brainwave","concept","conceptie","deductie","denkbeeld","denkpatroon","denkrichting","denktrant","denkwereld","denkwijze","droom","feit","gedachte","gedachtegang","gedachteloop","gedachtesprong","gegeven","geloof","gril","grondbeginsel","grondbegrip","grondbeschouwing","grondgedachte","grondregel","grondstelling","hoofdlijn","idee","inductie","intellect","inval","inzicht","kerngedachte","maxime","notie","onderstelling","overlegging","perspectief","postulaat","premisse","principe","propositie","redenatie","redenering","syllogisme","theorema","uitgangspunt","verbazing","vermoeden","veronderstelling","verstand","verwondering","vondst","voorgevoel","begeestering","bezieling","emotie","feeling","gevoel","gevoelen","sentiment"])

def isVZeg(node):
    return hasLemma(node, ["voel","voel_aan","observeer","neem_waar","zie","hoor","beluister","ruik","bedenk","bereken","beschouw","denk","geloof","verbaas","veronderstel","verwonder","accepteer","antwoord","bedoel","begrijp","beken","beklemtoon","bekrachtig","belijd","beschrijf","besef","bericht","betuig","bevestig","bevroed","beweer","bewijs","bezweer","biecht","breng","brul","concludeer","confirmeer","constateer","debiteer","declareer","demonstreer","denk","email","erken","expliceer","expliciteer","fantaseer","formuleer","geef_aan","hamer","herinner","houd_vol","kondig_aan","kwetter","licht_toe","maak_bekend","maak_hard","meld","merk","merk_op","motiveer","noem","nuanceer","onthul","ontsluier","ontval","ontvouw","oordeel","parafraseer","postuleer","preciseer","presumeer","pretendeer","publiceer","rapporteer","realiseer","redeneer","refereer","reken","roep","roer_aan","schat","schets","schilder","schreeuw","schrijf","signaleer","snap","snater","specificeer","spreek_uit","staaf","stel","stip_aan","suggereer","tater","teken_aan","toon_aan","twitter","verhaal","verklaar","verklap","verkondig","vermoed","verraad","vertel","vertel_na","verwacht","verwittig","verzeker","vind","waarschuw","wed","weet","wijs_aan","wind","zeg","zet_uiteen","twitter"])

def isVPassief(node): return hasLemma(node, ["dunk","lijk","kom_voor","schijn_toe","val_op"])
def isVEquiv(node):   return hasLemma(node, ["duid_aan", "duid", "karakteriseer","kenschets"])
def isVMoet(node):    return hasLemma(node, ["moet","behoor","dien"])
def isVBelofte(node): return hasLemma(node, ["beloof","zeg_toe","zweer"])
def isVolgens(node):  return hasLemma(node, ["volgens", "aldus"])
def isVoltooid(node): return hasLemma(node, ["doordring", "overtuigd", "bewust"])
def isBijzin(node):   return hasLemma(node, ["die","dat"])
def isSOdraai(node):  return hasLemma(node, ["krijg","ontvang"])
def isNBelofte(node):
    return hasLemma(node, ["belofte","toezegging","afspraak","gelofte","erewoord","overeenkomst","verbond","verbintenis","regeling","verdrag", "akkoord","contract","convenant","regeerakkoord","conventie"])
def isVVraag(node):
    return hasLemma(node, ["aarzel","bestudeer","bid","dub","filosofeer","smeek","soebat","twijfel","vraag","vraag_na","wacht_af","weifel","zeur"])
def isNVraag(node):
    return hasLemma(node,  ["aarzeling","geaarzel","geweifel","navraag","onderzoek","probleemstelling","strijdvraag","tweestrijd","vraag","vraagstelling","vraagstuk","weifeling"])
def isVOrder(node):
    return hasLemma(node, ["adviseer","bedreig","bekoor","beveel","beveel_aan","commandeer","decreteer","drijf","dwing","eis","forceer","gebied","gelast","hits_aan","hits_op","jaag_aan","lok_aan","maan","maan_aan","mandateer","moedig_aan","ordonneer","por","pres","prikkel","raad_aan","roep_op","spoor_aan","stimuleer","stook","stook_op","verleid","verlok","verorden","verordonneer","verplicht","verzoek","vorder","vuur_aan","zet_aan","zweep_op"])

def isNotDeterminer(node):
    return node and node.word.label not in ["de", "het", "een", "dit", "dat", "deze", "die"]
def isGoal(node):
    return hasLemma(node, ["bedoeling","bestemming","bijbedoeling","bijgedachte","doel","doeleinde","doelstelling","doelwit","doelwit","einddoel","hoofddoel","intentie","levensdoel","mikpunt","nevendoel","oogmerk","oogmerk","opzet","plan","strekking","streven","tussendoel","voornemen"])


################# Node Finding  #######################

def getTest(e):
    if not e: return lambda x: True
    if type(e) in (list, tuple, set): return e.__contains__
    return e.__eq__

def find(path, rel=None, word=None, lemma=None, pos=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    for n2, r in path:
        if word(n2.word.label) and lemma(n2.word.lemma.label) and pos(n2.word.lemma.pos) and rel(r):
            return n2

def findLast(path, rel=None, word=None, lemma=None, pos=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    result = None
    for n2, r in path:
        if word(n2.word.label) and lemma(n2.word.lemma.label) and pos(n2.word.lemma.pos) and rel(r):
            result = n2
        else:
            return result
    return result
        
def getChild(node, *cond, **kwcond):
    return find(node and node.getRelations(), *cond, **kwcond)

def getParent(node, *cond, **kwcond):
    return find(node and node.getParents(), *cond, **kwcond)
        
def getAncestor(node, *cond, **kwcond):
    return find(getAncestors(node), *cond, **kwcond)

def getRoot(node, *cond, **kwcond):
    return findLast(getAncestors(node), *cond, **kwcond)
    
def getDescendant(node, *cond, **kwcond):              
    return find(getDescendants(node), *cond, **kwcond)   

def getAncestors(node):
    if not node: return
    for n2, rel in node.getParents():
        yield n2, rel
        for n3, rel in getAncestors(n2):
            yield n3, rel

def getDescendants(node):
    if not node: return
    for n2, rel in node.getRelations():
        yield n2, rel
        for n3, rel in getDescendants(n2):
            yield n3, rel

                
def getSibling(node, uprel, *downcond, **kwdowncond):
    return getChild(getParent(node, uprel), *downcond, **kwdowncond)


################# Frame Definitions ########

class Frame(Identity):
    def __init__(self, name, **constituents):
        self.name = name
        for k,v in constituents.items():
            if k:
                self.__dict__[k] = v
        debug(self)
                    
    def isComplete(self):
        return True
    def get(self, name):
        return self.__dict__.get(name)
    def has(self, *names):
        for name in names:
            if not self.get(name): return False
        return True
    def getConstituents(self):
        return tuple(sorted((k,v) for (k,v) in self.__dict__.items()
                            if isinstance(v, parsetree.ParseNode)))

    def identity(self):
        return self.__class__, self.name, self.getConstituents()
    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.name,
                               ", ".join("%s=%s" % kv for kv in self.getConstituents()))
    
class BronFrame(Frame):
    def __init__(self, name, key=None, source=None, quote=None, addressee=None):
        Frame.__init__(self, name, key=key, source=source, quote=quote, addressee=addressee)
    def isComplete(self):
        return self.has('key', 'source', 'quote')

class SPOFrame(Frame):
    def __init__(self, name, subject=None, predicate=None, object=None, doelkey=None, doelobject=None):
        Frame.__init__(self, name, subject=subject, predicate=predicate, object=object, doelkey=doelkey, doelobject=doelobject)
    def isComplete(self):
        #if self.has('doelkey') ^ self.has('doelobject'): return false # ^ = XOR
        return self.has('subject','predicate','object')
    
################# Interface ################

def findBronnen(tree):
    for node in tree.getNodes():
        for name,func in sorted(globals().items()):
            if name.startswith('rule_'):
                frames = func(node)
                if type(frames) not in (list, set, tuple): frames = (frames,)
                for frame in frames:
                    if frame and frame.isComplete():
                        debug("YIELDING===>", frame=frame)
                        yield frame
                    elif frame:
                        debug("Skipping incomplete frame:", frame)


debug_hook = None
def debug(*args, **kargs):
    if not debug_hook: return

    debug_hook(sys._getframe(1).f_code.co_name + ": " + ", ".join(map(str, args) + ["%s=%s" % kv for kv in kargs.iteritems()]))
                
if __name__ == '__main__':
    import dbtoolkit, parsetree
    db = dbtoolkit.amcatDB()
    tree = parsetree.fromDB(db, 121)
    b = Bronnen(tree)
    b.prnt("/home/amcat/www-plain/test.png")
    
    

