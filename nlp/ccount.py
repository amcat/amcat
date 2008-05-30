import cnlp,array,re, toolkit

def bit(bool):
    if bool: return 1
    return 0

class Counter:
    def __init__(self, words):
        #print "Reading dictionary"
        l = words.items()
        self.l = l # keep a reference to avoid the strings being gc'ed
        self.hash = cnlp.initcount(l)
        toolkit.warn("initialized %i words" % len(l))

    def count(self, text, duplicate = True, lower=True, lemmapos=0):
        return cnlp.count(text, self.hash, bit(duplicate), bit(lower), lemmapos)
                
if __name__ == '__main__':
    words = {'de':1, 'kat':2, 'mat' : 3}
    c = Counter(words)
    text = "de kat zat op de mat "
    for k, c in c.count(text).items():
        print k, c
