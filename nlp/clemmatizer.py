import cnlp,array,re

POS_LEMMADICT_FILE = '/home/anoko/resources/wvalemma/lemmadict_pos.txt'
#POS_LEMMADICT_FILE = '/tmp/lemmasub.txt'

class Lemmatizer:
    def __init__(self, options="DEPRECATED", dictfile = POS_LEMMADICT_FILE):
        #print "Reading dictionary"
        import time; t = time.time()
        l = [("%s/%s" % (x[0],x[1]), x[2]) for x in [y.lower().strip().split("|") for y in open(dictfile).readlines()]]
        self.l = l # keep a reference to avoid the strings being gc'ed
        #print "Initializing cnlp.initlem %s" % (time.time() - t)
        self.hash = cnlp.initlem(l)
        #print "OK %s" % (time.time() - t)
        self.outputword = True

    def lemmatize(self, word):
        return cnlp.lemmatize(word, self.hash)

    def lemmatizeList(self, wordlist):
        import time
        t = time.time()
        totalp, totalc = 0,0
        result = array.array('c')
        #toolkit.ticker.interval = 1000
        list = re.split('(\s+)', wordlist)
        for l in list:
            if not l: continue
            if re.match('\s+', l):
                #print "whitespace %r" % l
                result.extend(l)
            else:
                if self.outputword:
                    result.extend(l)
                    result.append('/')
                l = l[:l.index('/')+2].lower()
                l2 = l
                totalp += time.time() - t
                t = time.time()
                l = self.lemmatize(l)
                totalc += time.time() - t
                t = time.time()
                #print "%r -> %r" % (l2, l)
                result.extend(l)
        result = "".join(result)
        totalp += time.time() - t
        #print "Total time: %1.4f, python:%1.4f, C:%1.4f" % (totalp+totalc, totalp, totalc)
        return result
                
if __name__ == '__main__':
    cl = Lemmatizer()
    print "Lemmatizing..."
    s = """panne/N(soort,ev,neut) op/Prep(voor) de/Art(bep,zijd_of_mv,neut) Weg/N(eigen,ev,neut) van/Prep(voor) de/Art(bep,zijd_of_mv,neut) Dood/N(soort,ev,neut) \n\nDOOR/N(eigen,ev,neut) ONZE/N(eigen,ev,neut) CORRESPONDENT/N(eigen,ev,neut) ERIK/N(eigen,ev,neut) VAN/Prep(voor) EES/N(eigen,ev,neut) \n\nHanover/N(eigen,ev,neut) (/Punc(haak_open) Zuid-Afrika/N(eigen,ev,neut) )/Punc(haak_sluit) -/Punc(ligg_streep) Op/Prep(voor) de/Art(bep,zijd_of_mv,neut) 1/Num(hoofd,bep,attr,onverv) ./Punc(punt) 400/Num(hoofd,bep,attr,onverv) kilometer/N(soort,ev,neut) lange/Adj(attr,stell,verv_neut) N1-snelweg/Num(hoofd,bep,zelfst,onverv) tussen/Prep(voor) \nJohannesburg/N(eigen,ev,neut) en/Conj(neven) Kaapstad/N(eigen,ev,neut) ligt/V(intrans,ott,3,ev) een/Art(onbep,zijd_of_onzijd,neut) traject/N(soort,ev,neut) dat/Pron(betr,neut,zelfst) bekend/Adj(attr,stell,onverv) staat/V(intrans,ott,3,ev) als/Conj(onder,met_fin) de/Art(bep,zijd_of_mv,neut) '/Punc(aanhaal_enk) Weg/N(eigen,ev,neut) van/Prep(voor) de/Art(bep,zijd_of_mv,neut) \nDood/N(soort,ev,neut) '/Punc(aanhaal_enk) ./Punc(punt) \n\nVanaf/Prep(voor) Richmond/N(eigen,ev,neut) tot/Prep(voor) Colesberg/N(eigen,ev,neut) zijn/Pron(bez,3,ev,neut,attr) ongelukken/N(soort,mv,neut) aan/Prep(voor) de/Art(bep,zijd_of_mv,neut) orde/N(soort,ev,neut) van/Prep(voor) de/Art(bep,zijd_of_mv,neut) dag/N(soort,ev,neut) ./Punc(punt) Onlangs/Adv(gew,geen_func,stell,onverv) \nnog/Adv(gew,geen_func,stell,onverv) verongelukten/N(soort,mv,neut) er/Adv(gew,er) zeven/Num(hoofd,bep,attr,onverv) mensen/N(soort,mv,neut) ./Punc(punt) Vooral/Adv(gew,geen_func,stell,onverv) in/Prep(voor) de/Art(bep,zijd_of_mv,neut) vakantietijd/N(soort,ev,neut) en/Conj(neven) tijdens/Prep(voor) lange/Adj(attr,stell,verv_neut) \nweekeinden/N(soort,mv,neut) stijgt/V(intrans,ott,3,ev) het/Art(bep,onzijd,neut) dodental/N(soort,ev,neut) explosief/Adj(attr,stell,onverv) ./Punc(punt) \n\nHanover/N(eigen,ev,neut) is/V(hulp_of_kopp,ott,3,ev) een/Art(onbep,zijd_of_onzijd,neut) dorp/N(soort,ev,neut) aan/Prep(voor)"""
    print `cl.lemmatizeList(s)`
