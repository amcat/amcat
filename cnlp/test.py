import cnlp

print "\n-------------\nTesting Lemmatize \n--------------"

list = """syncoperende|V|syncoperen
riviermosselen|N|riviermossel
kaaidraaiden|V|kaaidraaien
Bilbao|N|Bilbao
inweek|V|inweken""".split("\n")

list = [("%s/%s" % (x[0],x[1]), x[2]) for x in [y.split("|") for y in list]]

x = cnlp.initlem(list)

print "Pointer: %s" % x 

s = "inweek/N"; a = "inweek"
s2 = "boters/N"; a2 = "boter"
s3 = "tegen/P"; a3 = "tegen"

for s,a in zip((s,s2,s3),(a,a2,a3)):
    print "%s -> %s =?= %s" % (s, cnlp.lemmatize(s, x), a)
    
    if (cnlp.lemmatize(s, x) == a) and (cnlp.lemmatize(s2, x) == a2):
        print "OK!"
    else:
        print " >>>>>>>>> FAILED! <<<<<<<<<<"

print "\n-------------\nTesting Count \n--------------"

list = (
    ("de", 1),
    ("het", 2),
    ("kat", 3),
    ("kater", 3),
    ("blauwe", 5),
    ("mat", 6),
    )

x = cnlp.initcount(list)

print "Pointer: %s" % x 

s = "de blauwe kater ging met       de KaT naar   het huis  op de mat"
answer = {1: 3, 2: 1, 3: 2, 5: 1, 6:1}

result = cnlp.count(s,x,1,1, 0)
print "%s --> %s" % (s,result)
if (result == answer):
    print "OK"
else:
    print " >>>>>>>>> FAILED! <<<<<<<<<<"


print "\n-------------\nTesting Count lemmaPos \n--------------"

s = "tellende/V(trans,teg_dw,verv_neut)/tellen krant/N(soort,ev,neut)/krant ,/Punc(komma)/, zegt/V(trans,ott,3,ev)/zeggen dat/Conj(onder,met_fin)/dat het/Art(bep,onzijd,neut)/het opheffen/V(trans,inf,subst)/opheffen van/Prep(voor)/van het/Art(bep,onzijd,neut)/het Brabants/N(eigen,ev,neut)/brabants Nieuwsblad/N(eigen,ev,neut)/nieuwsblad een/Art(onbep,zijd_of_onzijd,neut)/een '/Punc(aanhaal_enk)/' verarming/N(soort,ev,neut)/verarming '/Punc(aanhaal_enk)/' betekent/V(trans,ott,3,ev)/betekenen in/Prep(voor)/in West-Brabant/N(eigen,ev,neut)/westbrabant is/V(hulp_of_kopp,ott,3,ev)/zijn zegt/V(trans,ott,3,ev)/zeggen Brader/N(eigen,ev,neut)/brader blij/Adj(adv,stell,onverv)/blij verrast/V(trans,verl_dw,onverv)/verrassen"

list = (
        ("het/R", 1),
        ("tellen/V", 2),
        ("brader/E", 3),
        ("zijn/X", 4),
        ("krant/N", 5),
        ("blij/J", 5),
        )

x = cnlp.initcount(list)
print "Pointer: %s" % x

answer = {1: 2, 2: 1, 3: 1, 4: 1, 5:2}

result = cnlp.count(s,x,1,0, 1)
print "%s --> %s" % (s,result)
if (result == answer):
    print "OK"
else:
    print " >>>>>>>>> FAILED! <<<<<<<<<<"

print "\n-------------\nTesting Count lemma \n--------------"

list = (
        ("het", 1),
        ("tellen", 2),
        ("brader", 3),
        ("zijn", 4),
        ("krant", 5),
        ("blij", 5),
        )

x = cnlp.initcount(list)
print "Pointer: %s" % x

answer = {1: 2, 2: 1, 3: 1, 4: 1, 5:2}

result = cnlp.count(s,x,1,0, 2)
print "%s --> %s" % (s,result)
if (result == answer):
    print "OK"
else:
    print " >>>>>>>>> FAILED! <<<<<<<<<<"


print "\n-------------\nTesting Count word \n--------------"

list = (
        ("het", 1),
        ("tellende", 2),
        ("brader", 3),
        ("is", 4),
        ("krant", 5),
        ("blij", 5),
        )

x = cnlp.initcount(list)
print "Pointer: %s" % x

answer = {1: 2, 2: 1, 3: 1, 4: 1, 5:2}

result = cnlp.count(s,x,1,1, 3)
print "%s --> %s" % (s,result)
if (result == answer):
    print "OK"
else:
    print " >>>>>>>>> FAILED! <<<<<<<<<<"


                

print "\n-------------\nTesting Tokenize \n--------------"

s = """Vice-voorzitter, z'n Laurent 'Heere' van de redactieraad van het Brabants
Nieuwsblad regageert 'verbijsterd' op het nieuws. 'De voorgenomen opheffing van
onze krant en de mogelijkheid dat er na het samengaan met De Stem in Breda
ontslagen vallen, moeten voor aanstaande dinsdag van tafel, anders volgen er
acties'. Zet u dhr. J. van Dijk, Drs. Z.K.H. Bea en prof. dr. Peter R. en Prof. Vrieske etc. A.U.B. z.s.m. in afl. drie buitenspel !"""
answer = """Vice-voorzitter , z'n Laurent ' Heere ' van de redactieraad van het Brabants \n Nieuwsblad regageert ' verbijsterd ' op het nieuws . ' De voorgenomen opheffing van \n onze krant en de mogelijkheid dat er na het samengaan met De Stem in Breda \n ontslagen vallen , moeten voor aanstaande dinsdag van tafel , anders volgen er \n acties ' . Zet u dhr. J. van Dijk , Drs. Z.K.H. Bea en prof. dr. Peter R. en Prof. Vrieske etc . A.U.B. z.s.m. in afl. drie buitenspel !"""

result = cnlp.tokenize(s)
print "%r --> %r" % (s[:30], result[:30])

if (result == answer):
    print "OK"
else:
    print " >>>>>>>>> FAILED! <<<<<<<<<<"
    print `s`
    print `result`
    print `answer`

print "\n-------------\n Testing wplToWc \n--------------"

s = "Directeur/N(soort,ev,neut)/directeur J/N(eigen,ev,neut)/j ./Punc(punt)/. Brader/N(eigen,ev,neut)/brader van/Prep(voor)/van het/Art(bep,onzijd,neut)/het Dagblad/N(eigen,ev,neut)/dagblad De/N(eigen,ev,neut)/de Stem/N(eigen,ev,neut)/stem is/V(hulp_of_kopp,ott,3,ev)/zijn '/Punc(aanhaal_enk)/' blij/Adj(adv,stell,onverv)/blij verrast/V(trans,verl_dw,onverv)/verrassen '/Punc(aanhaal_enk)/' over/Adv(deel_v)/over de/Art(bep,zijd_of_mv,neut)/de aangekondigde/V(trans,verl_dw,verv_neut)/aankondigen verkoop/N(soort,ev,neut)/verkoop van/Prep(voor)/van het/Art(bep,onzijd,neut)/het Brabants/N(eigen,ev,neut)/brabants Nieuwsblad/N(eigen,ev,neut)/nieuwsblad ./Punc(punt)/. Net/Adv(gew,geen_func,stell,onverv)/net als/Conj(onder,met_fin)/als collega/N(soort,ev,neut)/collega Verrest/N(eigen,ev,neut)/verrest ziet/V(trans,ott,3,ev)/zien"
a = "directeur/N j/E ./U brader/E van/P het/R dagblad/E de/E stem/E zijn/X '/U blij/J verrassen/V '/U over/A de/R aankondigen/V verkoop/N van/P het/R brabants/E nieuwsblad/E ./U net/A als/C collega/N verrest/E zien/V"

r = None
try:
    r = " ".join(cnlp.wplToWc(x) for x in s.split())
except:
    pass

if a == r:
    print "OK"
else:
    print " >>>>>>>>> FAILED! <<<<<<<<<<"
    for x,y in zip(s.split(), a.split()):
        r = cnlp.wplToWc(x)
        if r <> y:
            print x, r, y
    

# test robustness

for s in "Directeur/N(soort,ev,neut)", "Directeur", "Directeur/N(soort,ev,neut)/", "Directeur//", "//":
    print "%r -> %r" % (s, cnlp.wplToWc(s))
