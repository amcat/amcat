from idlabel import Identity
import sys, parsetree

_DB = None

#TODO: flexibere selectie-opties op get*(), bv lemma/rel/pos
#TODO: makkelijker debuggen

################ Main rules #################
# All rules starting with rule_* will be
# traversed in alphabetical order
################

    
def rule_bron_2_V(node):
    if isVZeg(node) or isVPassief(node): act="zeg"
    elif isVOntken(node): act="ontken"
    elif isVOrder(node): act="order"
    elif isVVraag(node): act="vraag"
    elif isVBelofte(node): act="belofte"
    else: return
    #debug("---------------------------------------------?",node,getParent(node," --"))
    frame = Bron(act, key=node)
    if isNiet(getChild(node, "mod")): frame.negation = getChild(node, "mod")  
#    if isNiet(getChild(node, "mod",word="niet" )): frame.negation = getChild(node, "mod",word="niet")
    ok = 0 
    if isVPassief(node): # passief: src=meewerkend vw., quote=subject, werkt niet met schijn_toe
        frame.source = getChild(node, "obj2")
        frame.quote = getChild(node, "su")
        ok = 1
    elif getParent(node,"tag"): # zie zin 39397183
        frame.source = getChild(node, "su")
        frame.quote = getParent(node, "tag")
        ok = 1
    elif getChild(node,"dp"):  #zinnen zonder , of : om citaat af te bakenen, 39404298 (zeg papa)
        frame.source = getChild(node,"su")
        frame.quote  = getChild(node,"dp")
        #return frame
        ok = 1
    elif getAncestor(node," --") and getParent(node,"dp"): #39397435 onacceptabel, oordeelde Bos gisteren over miljoenennota
        frame.source = getChild(node,"su")
        frame.quote = getChild(node,"pc")
        ok = 1
    elif getParent(node,"dp"):  #zinnen zonder , of : om citaat af te bakenen, 39397365 (zeg kind))
        frame.source = getChild(node,"su")
        frame.quote  = getParent(node,"dp")
        ok = 1
        #return frame
    else:
        frame.source = getChild(node, "su")
        frame.quote = getChild(node, ("vc","obj1","nucl"))
        ok = 1     
    if frame.source:   #39400763, uitbreidende isVzeg bijzin: Timmermans (mod) die (su) zei, had ook met getResolveSource gekund
        if frame.source.word.lemma.label in ("die","dat","welke","dewelke") and getParent(frame.source, "mod"):
            frame.source = getParent(frame.source, "mod")
#   dubieus of je isDat moet eisen, bv te stringent in Bos zei nee 39417441, daarom niet geeist als getChild "obj1"
    if isNGezegde(frame.source): #39417595
        frame.source,frame.quote = frame.quote,frame.source
    if frame.quote: frame.name = getMoetOrder(frame.quote,act)
    if (isVBelofte(node) or isVOrder(node)) and frame.source and getChild(node,"mod"):
        pdoel=getChild(node, "mod") #om-constructie hangt aan object, zie 39403134
        if pdoel.word.lemma.label in ("met het oog op", "om","omwille","opdat","zodat","waardoor","teneinde","voor"):
            frame.quote  = pdoel
            ok = 1
    doelframe = getDoel(node, frame.quote)
    if not(ok) and  not (isDat(frame.quote) and getChild(node, ("vc","nucl"))): return
    return [frame, doelframe]


def rule_bron_3_N(node):
    if isNGezegde(node): act="zeg"
    elif isNVraag(node): act="vraag"
    elif isNBelofte(node): act="belofte"
    else: return
    frame = Bron(act, key=node)
    # determine quote:
    # (1) vc "stelling dat ...",
    # (2) obj1, dp (hoe alpino abuisieelijk te werk gaat bij stellinganme),
    # (3) V->vc (bv "zou de mening hebben dat")),
    frame.quote = (getChild(node, "vc")
                   or getSibling(node, "obj1","dp") 
                   or getChild(getAncestor(node,pos="V"), "vc") # stelling van jan
                   or getDescendant(getAncestor(node," --"),"sat")) #uitleg jan: piet slaapt
    det = getChild(node, "det")
    if isNotDeterminer(det):
        frame.source =det
    else:
        frame.source = (getChild(getChild(node, "mod", word="van"), "obj1") # de stelling van jan dat ..
                        or getChild(getAncestor(node, pos="V"), "su"))      # jan poneert de stelling dat ...
    ok = 0
    if not frame.quote:  #31310 dit maakte twijfel los in Den Haag
        frame.quote = getChild(getParent(node,"obj1"),"su")
        frame.source = getChild(getChild(getParent(node,"obj1"),"mod",pos="P"),"obj1")
        ok = 1
    if frame.quote:
        frame=Bron(getMoetOrder(frame.quote,act),key=node,source=frame.source,quote=frame.quote,negation=frame.negation)
        ok = 1
    if not (isDat(frame.quote) or  getDescendant(getAncestor(node," --"),"sat") or ok) : return
    return frame

def rule_bron_4_volgens(node): # zie 39396066
    if not isVolgens(node): return
    frame = Bron("volgens", key=node)    
    frame.source = getChild(node, "obj1")
    frame.quote = (getParent(node, "mod")
                   or getParent(node, "tag"))
    rootverb = getRoot(frame.quote, pos='V') # zie 39396205
    if rootverb: frame.quote = rootverb
    return frame

def rule_bron_5_ervan(node): # zie 38667309 39397172
    if not isVoltooid(node): return
    frame = Bron("ervan", key=node)
    frame.source = (getChild(node, "obj1","pc")
                    or getSibling(node, "predc", "su"))
    frame.quote = getChild(getChild(node, "pc"), "vc")
    return frame

def rule_bron_6_directerede(node): # gaat mis bij 39397408
    dubbelepunt = getParent(node," --")     
    if dubbelepunt:
        if dubbelepunt.word.lemma.label.strip() == (":"):   #39417433
            frame=Bron("direde", key=dubbelepunt)
            frame.source = node
            frame.quote = getChild(node,"nucl") or getChild(node,"sat")
            if not frame.quote: #39397408
                for n2, rel in node.getRelations():
                    if rel == "dp" and getChild(n2, "su"): 
                        frame.quote = n2
                        break
            # debug ("xxxxx ",frame.key, frame.source, frame.quote)
            return frame

def rule_bron_7_voltooiddeelwoord(node):
    #is verrast over ... moet eigenlijk worden opgevangen door SPO1?actief if not frame.object: frame.object = getChild(getChild(node, "pc"),"obj1") 
    if not (node.word.lemma.pos=='A'  and getParent(node,"mod") and isVHulpww(getParent(node)) ): return
    frame = SPO("spo",predicate=node)
    frame.subject = getChild(getParent(node,"mod"),"su")
    frame.object = getChild(getChild(node,"pc"),"obj1")
    if not frame.object: frame.object = getChild(getParent(node,"mod"),"sat") 
    return frame

def isVnotZeg(node):
    return (node.word.lemma.pos == 'V'
            and not (isVZeg(node) or isVPassief(node) or isVOrder(node) or isVVraag(node) or isVBelofte(node)))

# doelmiddel bv 39403134

#def rule_bron_A_SPO1actief(node):
def rule_spo_1actief(node):
#   if isFrame(rule_bron**(node)): return
    if not isVnotZeg(node): return
    # only accept top verb in 'vc' chain with same su
    #if getChild(node, "su") and getChild(getParent(node,"vc"), "su") == getChild(node, "su"): return 
    frame = SPO("spo", predicate=node)
    frame.subject = getSubjectResolveDie(node)
    obj2p = getChild(node, "obj2", pos="P")
    frame.object = getChild(obj2p, "obj1")
    lowest = node
    while getChild(lowest, "vc"):
        lowest = getChild(lowest, "vc")
    if not frame.object: frame.object = getChild(lowest, "obj2") #object = MV
    if not frame.object:
        frame.object = getChild(lowest, "obj1")
    if not frame.object: frame.object = getChild(lowest, "predc") #of later, maar dan volgens bij mod uitsluiten
    if not frame.object:
        frame.object = getChild(getChild(lowest, "mod"),"obj1") #object=modMV
        if frame.object:
            hulp = getChild(lowest,"mod")
            if hulp.word.lemma.label in ("door"):
                frame.subject, frame.object = frame.object, frame.subject
    if not frame.object: frame.object = getChild(getChild(lowest, "pc"),"obj1")
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

def rule_spo_2passiefdoor(node):
    if not isVnotZeg(node): return
    frame = SPO("spo_door", predicate=node)
    hmod = getChild(node, rel="mod", pos="P")
    frame.subject = getChild(hmod,"obj1")
    frame.object  = getChild(node,"obj1")
    doBijzinSODraai(frame)
    return frame

#################### Hulpprocedures ########################dfasd

def getDoel(node, subject):
    frame = SPO("purp", subject=subject)
    pdoel=getChild(node, "mod")
    if not pdoel: pdoel = getChild(getAncestor(node,"vc",pos="V"),"mod")
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

def getMoetOrder(node,acta):
    if getDescendant(node,pos="V",lemma=["moet","betaam","behoor"]):
        debug("-------------------------------------------------,,,,,,,,,,,,,,,",node)
        acta="order" #39397178, moet in quote maakt het een bevel WERKT NOG NIET
    return acta

##################### Lexical definitions ########################

def isDat(node):
    return hasLemma(node, ["dat","of","te","wat","waardoor","waarom","waartoe","waarvoor"])

lemma_set_dict = {}

LEMMA_SQL = """select distinct l.lemmaid from words_lemmata l inner join words_words w on l.lemmaid = w.lemmaid inner join words_strings s on s.stringid = w.stringid where string in (%s)"""


def hasLemma(node, lemmata, pos=None):
    if not node: return
    key = (pos, tuple(lemmata))
    lset = lemma_set_dict.get(key)
    if not lset:
        SQL = LEMMA_SQL % (",".join("'%s'" % w for w in lemmata))
        if pos: SQL += "and pos ='%s'" % pos
        lset = set(lid for (lid,) in _DB.doQuery(SQL))
        lemma_set_dict[key] = lset
    return node.word.lemma.id in lset

def isNGezegde(node):
    return hasLemma(node, ["aankondiging","aanwijzing","achtergrondinformatie","affirmatie","anekdote","argument","argumentatie","assertie","begripsbepaling","bekendmaking","bekentenis","belijdenis","beoordeling","bericht","bescheid","bevestiging","bevinding","beweegreden ","bewering","bewijsvoering","bezegeling","biecht","boodschap","communicatie","communis opinio","conclusie","consequentie","constatering","convictie","denkbeeld","dienstbericht","dienstmededeling","diepte-informatie","dispositie","droombeeld","drijfveer","eed","eindconclusie","eindindruk","eindmening","eindoordeel","erkentenis","expressie","geest","geheim","gelukstijding","gerucht","geste","getuigenis","gevoelen","gevolgtrekking","gezichtspunt","gimmick","herinnering","hoofdargument","hoofdconclusie","impuls","indicatie","indruk","info","informatie","inlichting","inside-informatie","intuitie","jobspost","jobstijding","kreet","legende","levensbiecht","lezing","mare","mededeling","melding","meineed","melding","mening","motivering","nieuws","nieuwstijding","nieuwtje","notificatie","observatie","ondervinden","oordeel","openbaarmaking","openbaring","opinie","opmerking","opstelling","opvatting","overtuiging","overweging","positie","predictie","proclamatie","profetie","punt","rede","reden","relaas","repliek","revelatie","schuldbekentenis","schuldbelijdenis","slogan","slotbepaling","slotconclusie","slotindruk","slotsom","soundbite","spoedboodschap","standpunt","staving","stelling","stellingname","stokpaardje","suggestie","tegenbericht","tijding","tip","topic","totaalindruk","treurmare","uitdrukking","uiting","uitleg","uitspraak","verdediging","vergezicht","verhaal","verklaring","vertelling","vertolking","verwijzing","verwoording","verzekering","vingerwijzing","visie","volksovertuiging","voorspelling","voorstellingswijze","waarneming","weerwoord","wending","wereldopinie","woord","zienswijze","zinsnede","zinsuiting","abstractie","axioma","bedenksel","beginsel","benul","bewijs","bijgedachte","brainwave","concept","conceptie","deductie","denkbeeld","denkpatroon","denkrichting","denktrant","denkwereld","denkwijze","droom","feit","gedachte","gedachtegang","gedachteloop","gedachtesprong","gegeven","geloof","gril","grondbeginsel","grondbegrip","grondbeschouwing","grondgedachte","grondregel","grondstelling","hoofdlijn","idee","inductie","intellect","inval","inzicht","kerngedachte","maxime","notie","onderstelling","overlegging","perspectief","postulaat","premisse","principe","propositie","redenatie","redenering","syllogisme","theorema","uitgangspunt","verbazing","vermoeden","veronderstelling","verstand","verwondering","vondst","voorgevoel","begeestering","bezieling","emotie","feeling","gevoel","gevoelen","sentiment"], pos='N')


def isVZeg(node):
    return hasLemma(node, ["accepteer","antwoord","beaam","bedenk","bedoel","begrijp","beken","beklemtoon","bekrachtig","belijd","beluister","benadruk","bereken","bericht","beschouw","beschrijf","besef","betuig","bevestig","bevroed","beweer","bewijs","bezweer","biecht","breng","brul","concludeer","confirmeer","constateer","debiteer","declareer","demonstreer","denk","draag_uit","email","erken","expliceer","expliciteer","fantaseer","formuleer","geef_aan","geloof","hoor","hamer","herinner","houd_vol","kondig_aan","kwetter","licht_toe","maak_bekend","maak_hard","meld","merk","merk_op","motiveer","noem","nuanceer","observeer","onderschrijf","onderstreep","onthul","ontsluier","ontval","ontvouw","oordeel","parafraseer","postuleer","preciseer","presumeer","pretendeer","publiceer","rapporteer","realiseer","redeneer","refereer","reken","roep","roer_aan","ruik","schat","schets","schilder","schreeuw","schrijf","signaleer","snap","snater","specificeer","spreek_uit","staaf","stel","stip_aan","suggereer","tater","teken_aan","toon_aan","twitter","verbaas","verhaal","verklaar","verklap","verkondig","vermoed","veronderstel","verraad","vertel","vertel_na","verwacht","verwittig","verwonder","verzeker","vind","voel","voel_aan","waarschuw","wed","weet","wijs_aan","wind","zeg","zet_uiteen","zie","twitter"], pos='V')

def isVOntken(node):  return hasLemma(node, ["bestrijd","herroep","loochen","negeer","ontken","spreek_tegen","vecht_aan","veronachtzaam","verwaarloos","verwerp","weerleg","weerspreek"], pos='V')
def isVPassief(node): return hasLemma(node, ["dunk","lijk","kom_voor","schijn_toe","val_op"], pos='V')
def isVEquiv(node):   return hasLemma(node, ["duid_aan", "duid", "karakteriseer","kenschets"], pos='V')
def isVMoet(node):    return hasLemma(node, ["moet","behoor","dien"], pos='V')
def isVBelofte(node): return hasLemma(node, ["beloof","stel_voor","zeg_toe","zweer"], pos='V')
def isVolgens(node):  return hasLemma(node, ["volgens", "aldus"])
def isVoltooid(node): return hasLemma(node, ["doordring","overtuigd", "bewust"])
def isBijzin(node):   return hasLemma(node, ["die","dat"])
def isSOdraai(node):  return hasLemma(node, ["krijg","ontvang"], pos='V')
def isNBelofte(node):
    return hasLemma(node, ["belofte","toezegging","afspraak","gelofte","erewoord","overeenkomst","verbond","verbintenis","regeling","verdrag", "akkoord","contract","convenant","regeerakkoord","conventie"])
def isVVraag(node):
    return hasLemma(node, ["aarzel","bestudeer","bid","dub","filosofeer","smeek","soebat","twijfel","vraag","vraag_na","wacht_af","weifel","zeur"])
def isNVraag(node):
    return hasLemma(node,  ["aarzeling","geaarzel","geweifel","navraag","onderzoek","probleemstelling","strijdvraag","tweestrijd","twijfel","vraag","vraagstelling","vraagstuk","weifeling"])
def isVOrder(node):
    return hasLemma(node, ["adviseer","bedreig","bekoor","beveel","beveel_aan","commandeer","decreteer","drijf","dwing","eis","forceer","gebied","gelast","hits_aan","hits_op","hoop","jaag_aan","lok_aan","maan","maan_aan","mandateer","moedig_aan","ordonneer","por","pres","prikkel","raad_aan","roep_op","spoor_aan","stimuleer","stook","stook_op","verleid","verlok","verorden","verordonneer","verplicht","verzoek","vorder","vuur_aan","zet_aan","zweep_op"])
def isVerrast(node):  return hasLemma(node, ["verbaasd","verbouwereerd","verontwaardigd","verrast","versteld"], pos='A')
def isVHulpww(node):  return hasLemma(node, ["is","lijk","schijn","word"], pos='V')

def isNotDeterminer(node):
    return node and node.word.label not in ["de", "het", "een", "dit", "dat", "deze", "die"]
def isGoal(node):
    return hasLemma(node, ["bedoeling","bestemming","bijbedoeling","bijgedachte","doel","doeleinde","doelstelling","doelwit","doelwit","einddoel","hoofddoel","intentie","levensdoel","mikpunt","nevendoel","oogmerk","oogmerk","opzet","plan","strekking","streven","tussendoel","voornemen"],pos='N')
def isNiet(node): return hasLemma(node, ["geen","geenszins","nauwelijks","nergens","niet","nimmer","nooit","zonder"])


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

def getAncestors(node, stoplist=set()):
    if not node: return
    if node in stoplist: return
    stoplist.add(node)
    for n2, rel in node.getParents():
        yield n2, rel
        for n3, rel in getAncestors(n2, stoplist):
            yield n3, rel

def getDescendants(node, stoplist = set()):
    if not node: return
    if node in stoplist: return
    stoplist.add(node)
    for n2, rel in node.getRelations():
        yield n2, rel
        for n3, rel in getDescendants(n2, stoplist):
            yield n3, rel

                
def getSibling(node, uprel, *downcond, **kwdowncond):
    return getChild(getParent(node, uprel), *downcond, **kwdowncond)

def isFrame(frame, name=None):
    if not frame: return False
    if not frame.isComplete(): return False
    if name is None: return True
    if type(name) in (str, unicode): return frame.name == name
    return frame.name in name


################# Frame Definitions ########

class Frame(Identity):
    def __init__(self, name, *args, **kargs):
        self.name = name
        for i, k in enumerate(self.__class__.ARGS):
            v = args[i] if i < len(args) else None
            self.__dict__[k] = v
        for k,v in kargs.items():
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
    def getArgs(self):
        for argname in self.__class__.ARGS:
            arg = self.__dict__.get(argname)
            if not arg: break
            yield arg

    def identity(self):
        return self.__class__, self.name, self.getConstituents()
    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.name,
                               ", ".join("%s=%s" % kv for kv in self.getConstituents()))
    def __repr__(self):
        args = [arg.position for arg in self.getArgs()]
        kargs = {}
        for k,v in self.getConstituents():
            if v.position not in args:
                kargs[k] = v.position
        args = map(str, args)
        args += ["%s=%i" % (kv) for kv in kargs.items()]
        args = ",".join(args)
        return "%s(%s,%s)" % (self.__class__.__name__, `self.name`, args)
    def getNodesForConstituent(self, rol):
        constituents = self.getConstituents()
        stoplist = set([n for (r,n) in constituents])
        node = self.__getattribute__(rol)
        return set(node.getDescendants(stoplist=stoplist))

    def getNodesPerConstituent(self):
        for rol, node in self.getConstituents():
            yield rol, self.getNodesForConstituent(rol)
    
class Bron(Frame):
    ARGS = ["key","source","quote","addressee","negation"]
    def isComplete(self):
        return self.has('key', 'source', 'quote')

class SPO(Frame):
    ARGS = ["subject","predicate","object","doelkey","doelobject"]
    def isComplete(self):
        #if self.has('doelkey') ^ self.has('doelobject'): return false # ^ = XOR
        if self.has('subject','predicate','object'): return True
        return False
        if self.has('subject', 'predicate'):
            self.name = 'SPO_su'
            return True
        if self.has('object', 'predicate'):
            self.name = 'SPO_obj'
            return True
        return False

    
################# Interface ################

def findBronnen(tree):
    frames = map(getFrame, tree.getNodes())
    frames = [f for f in frames if f]
    return frames

def getFrame(node):
    for name,func in sorted(globals().items()):
        if name.startswith('rule_'):
            frames = func(node)
            if type(frames) not in (list, set, tuple): frames = (frames,)
            for frame in frames:
                if frame and frame.isComplete():
                    debug("RETURNING ===>", frame=frame)
                    return frame

                        
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
    
    

