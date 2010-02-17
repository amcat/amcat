from toolkit import Identity

################ Main rules #################
# All rules starting with getBron_* will be
# traversed in alphabetical order
################

def getBron_1(node):
    if isVZeg(node.word): act="zeg"
    elif isVOrder(node.word): act="order"
    elif isVVraag(node.word): act="vraag"
    else: return
    if isNiet(node): act = "ontken"
    su = getSu(node)
    q = getComplOrObj(node)
    if not (su and q): return
    return su, q, act 

def getBron_N(node):
    if not isNGezegde(node.word): return
    q = getChild(node, "vc") 
    if isNotDeterminer(getChild(node, "det")):
      su = getChild(node, "det")
    elif getChild(node, "mod"):
      mod = getChild(node, "mod")
      if mod.label in ["van"]: su = getChild(getChild(node, "mod"), "obj1")
      else: return
    else:
      hebben = getAncestor(node, "V")
      if not hebben: return
      su = getChild(hebben, "su")
    if not (su and q): return
    return su, q, "zeg" 
    

def isNiet(node):
    mod = getChild(node, "mod")
    if not mod: return False
    if mod.word.lemma.label in ["niet"]: return True
    return False
	


def isNGezegde(word):
    return word.lemma.label in ["aankondiging","aanwijzing","achtergrondinformatie","affirmatie","anekdote","argument","argumentatie","assertie","begripsbepaling","bekendmaking","bekentenis","belijdenis","beoordeling","bericht","bescheid","bevestiging","bevinding","beweegreden ","bewering","bewijsvoering","bezegeling","biecht","boodschap","communicatie","communis opinio","conclusie","consequentie","constatering","convictie","dienstbericht","dienstmededeling","diepte-informatie","dispositie","drijfveer","eed","eindconclusie","eindindruk","eindmening","eindoordeel","erkentenis","expressie","geest","geheim","gelukstijding","gerucht","geste","getuigenis","gevoelen","gevolgtrekking","gezichtspunt","gimmick","herinnering","hoofdargument","hoofdconclusie","impuls","indicatie","indruk","info","informatie","inlichting","inside-informatie","intuitie","jobspost","jobstijding","kreet","legende","levensbiecht","lezing","mare","mededeling","meineed.","melding","mening","motivering","nieuws","nieuwstijding","nieuwtje","notificatie","observatie","ondervinden","oordeel","openbaarmaking","openbaring","opinie","opmerking","opstelling","opvatting","overtuiging","overweging","positie","predictie","proclamatie.","profetie","punt","rede","reden ","relaas","repliek","revelatie","schuldbekentenis","schuldbelijdenis","slogan","slotbepaling.","slotconclusie","slotindruk","slotsom","soundbite","spoedboodschap","standpunt","staving","stelling","stellingname.","stokpaardje","suggestie","tegenbericht","tijding","tip.","topic","totaalindruk","treurmare","uitdrukking","uiting","uitspraak","verdediging","vergezicht","verhaal","verklaring","vertelling","vertolking","verwijzing","verwoording","verzekering","vingerwijzing","visie","volksovertuiging","voorspelling","voorstellingswijze","waarneming","weerwoord","wending","wereldopinie","woord","zienswijze","zinsnede","zinsuiting","abstractie","axioma","bedenksel","beginsel","benul","bewijs","bijgedachte","brainwave","concept","conceptie","deductie","denkbeeld","denkpatroon","denkrichting","denktrant","denkwereld","denkwijze","droom","feit","gedachte","gedachtegang","gedachteloop","gedachtesprong","gegeven","geloof","gril","grondbeginsel","grondbegrip","grondbeschouwing","grondgedachte","grondregel","grondstelling","hoofdlijn","idee","inductie","intellect","inval","inzicht","kerngedachte","maxime","notie","onderstelling","overlegging","perspectief","postulaat","premisse","principe","propositie","redenatie","redenering","syllogisme","theorema","uitgangspunt","verbazing","vermoeden","veronderstelling","verstand","verwondering","vondst","voorgevoel","begeestering","bezieling","emotie","feeling","gevoel","gevoelen","sentiment"] 

def isNotDeterminer(word):
    if not word: return False
    return word.label not in ["de", "het", "een", "dit", "dat", "deze", "die"]

def isVZeg(word):
    return word.lemma.label in ["voel","voel_aan","observeer","neem_waar","zie","hoor","beluister","ruik","bedenk","bereken","beschouw","denk","geloof","verbaas","veronderstel","verwonder","accepteer","antwoord","bedoel","begrijp","beken","beklemtoon","bekrachtig","belijd","beschrijf","besef","betuig","bevestig","bevroed","beweer","bewijs","bezweer","biecht","breng","brul","concludeer","confirmeer","debiteer","declareer","demonstreer","denk","duid","duid_aan","email","erken","expliceer","expliciteer","fantaseer","formuleer","geef_aan","hamer","herinner","houd_vol","karakteriseer","kondig_aan","kwetter","maak_bekend","maak_hard","meld","merk","merk_op","motiveer","nuanceer","onthul","ontsluier","ontval","ontvouw","oordeel","parafraseer","postuleer","preciseer","presumeer","pretendeer","publiceer","rapporteer","realiseer","redeneer","refereer","reken","roep","roer_aan","schat","schets","schilder","schreeuw","schrijf","signaleer","snap","snater","specificeer","staaf","stel","stip_aan","suggereer","tater","teken_aan","toon_aan","twitter","verhaal","verklaar","verklap","verkondig","vermoed","verraad","vertel","vertel_na","verwacht","verwittig","verzeker","vind","waarschuw","weet","wijs_aan","wind","zeg","zweer","verafschuw","twitter"]

def isVOrder(word):
    return word.lemma.label in ["adviseer","bedreig","bekoor","beveel","beveel_aan","commandeer","decreteer","drijf","dwing","eis","forceer","gebied","gelast","hits_aan","hits_op","jaag_aan","lok_aan","maan","maan_aan","mandateer","moedig_aan","ordonneer","por","pres","prikkel","raad_aan","spoor_aan","stimuleer","stook","stook_op","verleid","verlok","verorden","verordonneer","verplicht","verzoek","vorder","vuur_aan","zet_aan","zweep_op"]
    
def isVVraag(word):
    return word.lemma.label in ["aarzel","bestudeer","bid","dub","filosofeer","smeek","soebat","twijfel","vraag","vraag_na","wacht_af","weifel","zeur"]

def isNVraag(word):
    return word.lemma.label in ["aarzeling","geaarzel","geweifel","navraag","onderzoek","probleemstelling","strijdvraag","tweestrijd","vraagstelling","vraagstuk","weifeling"]

################# Relations #################

def getSu(node):
    return getChild(node, ("su",))

def getComplOrObj(node):
    return getCompl(node) or getObj(node)

def getCompl(node):
    return getChild(node, ("vc",))
def getObj(node):
    return getChild(node, ("obj1",))
    
################# Aux #######################

def getChild(node, rel):
    if type(rel) not in (list, tuple, set):
        rel = (rel,)
    for n, r in node.getRelations():
        if r in rel:
            return n
    
def getAncestor(node, pos):
    for n2, rel in node.getParents():
      if n2.word.lemma.pos == pos: return n2
      result = getAncestor(n2, pos)
      if result: return result
        

################# Interface ################


class Bron(Identity):
    def __init__(self, tree, key, source, quote, speechAct="zeg"):
        Identity.__init__(self,  tree, key, source, quote, speechAct)
        self.tree = tree
        self.key = key
        self.source = source
        self.quote = quote
        self.speechAct = speechAct

def findBronnen(tree):
    for node in tree.getNodes():
        for name,func in sorted(globals().items()):
            if name.startswith('getBron_'):
                r = func(node)
                if r:
                    su, q, speechAct = r
                    yield Bron(tree, node, su, q, speechAct)
                    break


if __name__ == '__main__':
    import dbtoolkit, parsetree
    db = dbtoolkit.amcatDB()
    tree = parsetree.fromDB(db, 121)
    b = Bronnen(tree)
    b.prnt("/home/amcat/www-plain/test.png")
    
    

