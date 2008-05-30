import re

POSMAP = {'W' : 'V', 'B' : 'A'}
POSMAP = {'V' : 'W', 'A' : 'B'}

class Wordlists:

    def __init__(self, wordlists):
        self.wordlists = wordlists

    def score(self, word):
        #print "'%s'" % word
        w = word[word.rindex("/")+1:] #lemma
        p = word[word.index("/")+1]   #POS
        wp = w + "/" + POSMAP.get(p,p)
        return map(lambda wl: wl.score(wl.usepos and wp or w), self.wordlists) # safe since wp cannot be false

    def scoretext(self, text):
        scores = [0.] * len(self.wordlists)
        for word in re.split("\s+", text):
            if not word: continue
            res = self.score(word)
            scores = map(lambda x,y: x+y, scores, res)
        return scores

    def overview(self, printlist = 0):
        res = ""
        for wl in self.wordlists:
            res += " %s : %s words\n" % (wl.name, len(wl.wordlist))
            if printlist:
                for w,s in wl.wordlist.items()[:20]:
                    res += "   %s : %s\n" % (w,s)
        return res

    def header(self):
        return map(lambda x:x.name, self.wordlists)
    
class Wordlist:

    def __init__(self, wordlist, usepos = 0, name = None):
        self.wordlist = wordlist
        self.usepos = usepos
        self.name = name

    def score(self,word):
        #print "%s scoring '%s' : %s" % (self.name, word, self.wordlist.get(word, 0))
        #print "%s scoring %s : %s" % (self.name, word, self.wordlist.get(word,0))
        return self.wordlist.get(word, 0)

def wordlistFromTable(table, name=None):
    """
    table should be a sequence of (word, score) or (word,pos,score) sequences
    Returns a Wordlist with the words (or word/pos) as keys and scores as dictionary
    """
    dict = {}
    for row in table:
        if len(row) > 2:
            key = "%s/%s" % (row[0], row[1])
            val = row[2]
            usepos = 1
        else:
            key = row[0]
            val = row[1]
            usepos = 0
        dict[key] = val

    return Wordlist(dict, usepos, name)

def wordlistsFromTable(table, name=""):
    """
    table should be a sequence of (cat,word, score) or (cat,word,pos,score) sequences
    Returns a list of Wordlist objects with the words (or word/pos) as keys and scores
    as dictionary, one for each different cat.
    """
    dicts = {}
    usepos = {}
    for row in table:
        cat = row[0]
        if len(row) > 3:
            key = "%s/%s" % (row[1], row[2])
            val = row[3]
            usepos[cat] = 1
        else:
            key = row[1]
            val = row[2]
            usepos[cat] = 0

        # zeroes can never influence:
        if not val:
            continue

        if cat not in dicts:
            dicts[cat] = {}
        try:
            dicts[cat][key] = float(val)
        except Exception, e:
            print row
            raise
    
    return map(lambda x:Wordlist(dicts[x],usepos[x], "%s%s" % (name,x)), dicts.keys())

if __name__ == '__main__':
    wls = []
    wls.append(Wordlist({"informatie" : 1, "over" : 10},0, 'simpel1'))
    wls.append(Wordlist({"kind/N" : 1, "kind/V" : 10},1, 'simpel2'))

    import dbtoolkit
    db = dbtoolkit.anokoDB()

    table = db.doQuery("select word, pos, sum(extrem2 * ambi2) from esther_1a group by word, pos")
    wls.append(wordlistFromTable(table, "tab1"))

    table = db.doQuery("select cat_sk, word, pos, Sum(cat_ex / n_word_pos) from brouwers_entries b inner join brouwers_cats c on b.cat = c.id group by cat_sk, word, pos")
    wlss = wordlistsFromTable(table, "tab2")
    print wlss
    wls += wlss

    wls = Wordlists(wls)

    
    import sys
    print "|".join(map(lambda x:"%s"%x, wls.header()))
    print "|".join(map(lambda x:"%s"%x, wls.scoretext(sys.stdin.read())))
