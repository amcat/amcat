import toolkit, sys, re, Levenshtein

SeRQL = """
SELECT X, lbl FROM
{X} rdfs:label {lbl}
""" 

class Labels:
    def __init__(self, db):
        self.labels = {}
        self.uris = {}
        for obj, lbl in db.execute(SeRQL):
            if obj in self.labels:
                toolkit.warn("Duplicate label for %s" % obj)
            self.labels[obj] = lbl
            lbl = lbl.lower()
            if lbl in self.uris:
                pass#toolkit.warn("Duplicate label, uris %s and %s" % (obj, self.uris[lbl]))
            else:
                self.uris[lbl] = obj

    def lookup(self, word):
        if word is None: return None
        res = self.labels.get(word, None)
        if res: return res
        return "~%s" % re.split("[/#]", word)[-1]

    def search(self, word, nmatches = 10):
        word = word.lower()
        #if word in self.uris:
        #    return self.uris[word]
        res = TopN(nmatches)
        for uri, label in self.labels.items():
            res.add(uri, score(word, label))
        return res

def l_score(word1, word2):
    return Levenshtein.ratio(unicode(word1), unicode(word2))

def jw_score(word1, word2):
    return Levenshtein.jaro_winkler(unicode(word1), unicode(word2))

score = jw_score
        
class TopN(object):
    def __init__(self, N=10):
        self.top = [None] * N
        self.scores = [None] * N

    def add(self, word, score):
        for i, s in enumerate(self.scores):
            if score > s:
                self.top = self.top[:i] + [word] + self.top[i:len(self.top)-1]
                self.scores = self.scores[:i] + [score] + self.scores[i:len(self.scores)-1]
                return

    def __str__(self):
        return str(self.top)


if __name__ == '__main__':
    import rdftoolkit
    db = rdftoolkit.anokoRDF()
    print db.getLabels().search(sys.argv[1])

