V_PASSIVE_SPEECH_ACTS = ('V', {
        "zeg" : ("dunk","lijk","kom_voor","schijn_toe","val_op"),
        })

ZEG_LEMMATA =  "accepteer","antwoord","beaam","bedenk","bedoel","begrijp","beken","beklemtoon","bekrachtig","belijd","beluister","benadruk","bereken","bericht","beschouw","beschrijf","besef","betuig","bevestig","bevroed","beweer","bewijs","bezweer","biecht","breng","brul","concludeer","confirmeer","constateer","debiteer","declareer","demonstreer","denk","draag_uit","email","erken","expliceer","expliciteer","fantaseer","formuleer","geef_aan","geloof","hoor","hamer","herinner","houd_vol","kondig_aan","kwetter","licht_toe","maak_bekend","maak_hard","meld","merk","merk_op","motiveer","noem","nuanceer","observeer","onderschrijf","onderstreep","onthul","ontsluier","ontval","ontvouw","oordeel","parafraseer","postuleer","preciseer","presumeer","pretendeer","publiceer","rapporteer","realiseer","redeneer","refereer","reken","roep","roer_aan","ruik","schat","schets","schilder","schreeuw","schrijf","signaleer","snap","snater","specificeer","spreek_uit","staaf","stel","stip_aan","suggereer","tater","teken_aan","toon_aan","twitter","verbaas","verhaal","verklaar","verklap","verkondig","vermoed","veronderstel","verraad","vertel","vertel_na","verwacht","verwittig","verwonder","verzeker","vind","voel","voel_aan","waarschuw","wed","weet","wijs_aan","wind","zeg","zet_uiteen","zie","twitter"
BELOOF_LEMMATA = "beloof","stel_voor","zeg_toe","zweer"

V_SPEECH_ACTS = ('V', {
    "zeg" : ZEG_LEMMATA,
    "ontken" : ("bestrijd","herroep","loochen","negeer","ontken","spreek_tegen","vecht_aan","veronachtzaam","verwaarloos","verwerp","weerleg","weerspreek"),
    "belofte" : BELOOF_LEMMATA,
    "order" : ("adviseer","bedreig","bekoor","beveel","beveel_aan","commandeer","decreteer","drijf","dwing","eis","forceer","gebied","gelast","hits_aan","hits_op","hoop","jaag_aan","lok_aan","maan","maan_aan","mandateer","moedig_aan","ordonneer","por","pres","prikkel","raad_aan","roep_op","spoor_aan","stimuleer","stook","stook_op","verleid","verlok","verorden","verordonneer","verplicht","verzoek","vorder","vuur_aan","zet_aan","zweep_op"),
    'vraag' : ("aarzel","bestudeer","bid","dub","filosofeer","smeek","soebat","twijfel","vraag","vraag_na","wacht_af","weifel","zeur"),
    })


N_GEZEGDE_LEMMATA = ("aankondiging","aanwijzing","achtergrondinformatie","affirmatie","anekdote","argument","argumentatie","assertie","begripsbepaling","bekendmaking","bekentenis","belijdenis","beoordeling","bericht","bescheid","bevestiging","bevinding","beweegreden ","bewering","bewijsvoering","bezegeling","biecht","boodschap","communicatie","communis opinio","conclusie","consequentie","constatering","convictie","denkbeeld","dienstbericht","dienstmededeling","diepte-informatie","dispositie","droombeeld","drijfveer","eed","eindconclusie","eindindruk","eindmening","eindoordeel","erkentenis","expressie","geest","geheim","gelukstijding","gerucht","geste","getuigenis","gevoelen","gevolgtrekking","gezichtspunt","gimmick","herinnering","hoofdargument","hoofdconclusie","impuls","indicatie","indruk","info","informatie","inlichting","inside-informatie","intuitie","jobspost","jobstijding","kreet","legende","levensbiecht","lezing","mare","mededeling","melding","meineed","melding","mening","motivering","nieuws","nieuwstijding","nieuwtje","notificatie","observatie","ondervinden","oordeel","openbaarmaking","openbaring","opinie","opmerking","opstelling","opvatting","overtuiging","overweging","positie","predictie","proclamatie","profetie","punt","rede","reden","relaas","repliek","revelatie","schuldbekentenis","schuldbelijdenis","slogan","slotbepaling","slotconclusie","slotindruk","slotsom","soundbite","spoedboodschap","standpunt","staving","stelling","stellingname","stokpaardje","suggestie","tegenbericht","tijding","tip","topic","totaalindruk","treurmare","uitdrukking","uiting","uitleg","uitspraak","verdediging","vergezicht","verhaal","verklaring","vertelling","vertolking","verwijzing","verwoording","verzekering","vingerwijzing","visie","volksovertuiging","voorspelling","voorstellingswijze","waarneming","weerwoord","wending","wereldopinie","woord","zienswijze","zinsnede","zinsuiting","abstractie","axioma","bedenksel","beginsel","benul","bewijs","bijgedachte","brainwave","concept","conceptie","deductie","denkbeeld","denkpatroon","denkrichting","denktrant","denkwereld","denkwijze","droom","feit","gedachte","gedachtegang","gedachteloop","gedachtesprong","gegeven","geloof","gril","grondbeginsel","grondbegrip","grondbeschouwing","grondgedachte","grondregel","grondstelling","hoofdlijn","idee","inductie","intellect","inval","inzicht","kerngedachte","maxime","notie","onderstelling","overlegging","perspectief","postulaat","premisse","principe","propositie","redenatie","redenering","syllogisme","theorema","uitgangspunt","verbazing","vermoeden","veronderstelling","verstand","verwondering","vondst","voorgevoel","begeestering","bezieling","emotie","feeling","gevoel","gevoelen","sentiment")

VOLGENS_ACTS = ('P', {"zeg": ("volgens", "aldus")})
VOLTOOID_ACTS = (None, {"weet" : ("doordring","overtuigd", "bewust")})
DIREDE_ACTS = ('.', {"zeg": (":",)})

DOELWOORDEN =  ("om","omwille","opdat","zodat","waardoor","teneinde","voor")
MIDDELWOORDEN = ("door","door middel van","via")
DETERMINERS = ("de", "het", "een", "dit", "dat", "deze", "die")
NEGATORS = ("geen","geenszins","nauwelijks","nergens","niet","nimmer","noch","nooit","zonder")

N_SPEECH_ACTS = ('N', {
        "zeg" : N_GEZEGDE_LEMMATA,
        "vraag" : ("aarzeling","geaarzel","geweifel","navraag","onderzoek","probleemstelling","strijdvraag","tweestrijd","twijfel","vraag","vraagstelling","vraagstuk","weifeling"),
        "belofte" : ("belofte","toezegging","afspraak","gelofte","erewoord","overeenkomst","verbond","verbintenis","regeling","verdrag", "akkoord","contract","convenant","regeerakkoord","conventie"),
        })

V_DRAAI = "krijg","ontvang"

#     "equiv" : ('V', ("duid_aan", "duid", "karakteriseer","kenschets")),
#     "moet" : ('V', ("moet","behoor","dien")),
#     "volgens" : (None, ("volgens", "aldus")),
#     "voltooid" : (None, ("doordring","overtuigd", "bewust")),
#     "bijzin" : (None
# def isBijzin(node):   return hasLemma(node, ["die","dat"])
# def isSOdraai(node):  return hasLemma(node, ["krijg","ontvang"], pos='V')
# def isVOrder(node):
#     return hasLemma(node, ["adviseer","bedreig","bekoor","beveel","beveel_aan","commandeer","decreteer","drijf","dwing","eis","forceer","gebied","gelast","hits_aan","hits_op","hoop","jaag_aan","lok_aan","maan","maan_aan","mandateer","moedig_aan","ordonneer","por","pres","prikkel","raad_aan","roep_op","spoor_aan","stimuleer","stook","stook_op","verleid","verlok","verorden","verordonneer","verplicht","verzoek","vorder","vuur_aan","zet_aan","zweep_op"])
# def isVerrast(node):  return hasLemma(node, ["verbaasd","verbouwereerd","verontwaardigd","verrast","versteld"], pos='A')
# def isVHulpww(node):  return hasLemma(node, ["is","lijk","schijn","word"], pos='V')

# def isNotDeterminer(node):
#     return node and node.word.label not in ["de", "het", "een", "dit", "dat", "deze", "die"]
# def isGoal(node):
#     return hasLemma(node, ["bedoeling","bestemming","bijbedoeling","bijgedachte","doel","doeleinde","doelstelling","doelwit","doelwit","einddoel","hoofddoel","intentie","levensdoel","mikpunt","nevendoel","oogmerk","oogmerk","opzet","plan","strekking","streven","tussendoel","voornemen"],pos='N')
# def isNiet(node): return hasLemma(node, ["geen","geenszins","nauwelijks","nergens","niet","nimmer","nooit","zonder"])
