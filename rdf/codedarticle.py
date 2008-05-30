import toolkit, math

class CodedArticle:
    def __init__(self, article, annotations = None):
        self.codedunits = {}
        self.article = article
        self.annotations = annotations or {}

    def addSentence(self, coder, unit, kernzin):
        #print "addiong %s %s %s : %s" % (self.article.id, coder, unit, kernzin)
        if coder not in self.codedunits: self.codedunits[coder] = CodedUnit(self, coder)
        self.codedunits[coder].addSentence(unit, kernzin)
        

    def coders(self):
        return self.codedunits.keys()

    def allUnits(self):
        """determine which units exist (ie are coded by somebody
        for this article, headline always exists"""
        units = set()
        for coder in self.coders():
            units |= set(self.codedunits[coder].units())
        return units

    def aid(self):
        if self.article: return self.article.id
        return None

    def irrelevant(self, coder):
        #print "checking %s : %s" % (self.article.id, coder)
        irrel = self.annotations.get(coder, {}).get("net:Irrelevant", None)
        #print irrel
        if irrel is not None:
            return irrel.lower() == 'true'
        cu = self.codedunits.get(coder, None)
        #print cu
        if not cu: return None
        for unit in cu.units():
            #print unit, cu.isCoded(unit)
            if cu.isCoded(unit):
                return False
        return True
        

class CodedUnit:
    def __init__(self, codedarticle, coder):
        self.codedarticle = codedarticle
        self.coder = coder
        self.sentences = toolkit.DefaultDict(list) # {unit : [sentences,..], ..}

    def isCoded(self, unit = None):
        if unit is None:
            return not not self.sentences
        else:
            return unit in self.sentences

    def getNSents(self, unit = None):
        if unit is None:
            result = []
            for unit in self.sentences:
                result += self.sentences[unit]
            return result
        else:
            return len(self.sentences.get(unit, []))

    def getSentences(self, unit):
        return self.sentences.get(unit, [])

    def addSentence(self, unit,  kernzin):
        self.sentences[unit].append(kernzin)

    def units(self):
        return self.sentences.keys()
        
    def __str__(self):
        return '<codedarticle coder="%s" id="%s" />' % (self.coder, self.codedarticle.aid())

def fromKernzinnen(zinnen, articleannot, db):
    articles = {} # {articleid : Article, ...}
    coders = set()
    for k in zinnen:
        aid = k.article.id
        coder = k.coder
        # ad hoc
        if coder == 'nel': coder = 'janet'
        if coder in ('wva','app','jan'): continue
        
        unit = k.unit
        coders.add(coder)
        if aid not in articles:
            articles[aid] = CodedArticle(db.article(aid), articleannot.get(aid, None))
        articles[aid].addSentence(coder, unit, k)
    for aid, annot in articleannot.items():
        if aid not in articles:
            articles[aid] = CodedArticle(db.article(aid), annot)
    
    return coders, articles
                                            

def articleAnnotsFromSesame(rdfdb = None, batches = None, where = None):
    if not rdfdb: rdfdb = rdftoolkit.anokoRDF()
    SeRQL = """
    SELECT An, Coder, Rel, X, Article FROM
    {An} Rel {X};
         dc:author {Coder};
         dc:subject {Article} anoko:InBatch {Batch}
    """
    if not where: where = []
    elif toolkit.isString(where): where = [where]
    if batches: where.append(' OR '.join(['(Batch = "%s"^^xsd:int)' % b for b in batches]))
    if where: SeRQL += ' WHERE (%s)' % ')\nAND ('.join(where)

    result = {} # {aid : {coder : {relatie : waarde, }, }, }
    for an, coder, rel, x, article in rdfdb.execute(SeRQL):
        aid = int(article.split("-")[-1])
        coder = coder.split("-")[-1]
        # ad hoc
        if coder == 'nel': coder = 'janet'
        if coder in ('wva','app','jan'): continue
        
        rel = rdfdb.nscollapse(rel)
        if not aid in result: result[aid] = {}
        if not coder in result[aid]: result[aid][coder] = {}
        result[aid][coder][rel] = x
    return result

def explanationHeaders():
    return "Kop",  "Subject1", "SubjSuper1", "Direction1", "Object1", "ObjSuper1", "Subject2", "SubjSuper1", "Direction2", "Object2", "ObjSuper2", "SubjectDist", "DirectionDist", "ObjectDist", "Distance"

def distance(s1, s2, explain=False, comparecategory = False, oordeelex = False):
    if s1 is None or s2 is None: return 99

    s1s = s1.subject
    s1q = s1.quality
    s1o = s1.object
    s2s = s2.subject
    s2q = s2.quality
    s2o = s2.object
    if oordeelex:
        if s2.object.url == 'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-3-ideal':
            s2o = s2s
            s2s = s2.source or s2.object
        if s1.object.url == 'http://www.content-analysis.org/vocabulary/ontologies/k06#kenobj-3-ideal':
            s1o = s1s
            s1s = s1.source or s1.object
    if comparecategory:
        if s1s.cat_af()[2]: s1q *= s1s.cat_af()[2]
        s1s = s1s.cat_af()[1]
        if s1o.cat_if()[2]: s1q *= s1o.cat_if()[2]
        s1o = s1o.cat_if()[1]
        if s2s.cat_af()[2]: s2q *= s2s.cat_af()[2]
        s2s = s2s.cat_af()[1]
        if s2o.cat_if()[2]: s2q *= s2o.cat_if()[2]
        s2o = s2o.cat_if()[1]
        
    dirdist = ((s1q - s2q) ** 2)/4
    subjectdist = 1-int(s1s == s2s)
    objectdist = 1-int(s1o == s2o)
    dist = float(dirdist + subjectdist + objectdist) / 3
    #if labels:
    #    s1s,s1o,s2s,s2o,s1ss, s1oo, s2ss, s2oo = [labels.lookup(x) for x in (s1s, s1o, s2s, s2o, s1.subject, s1.object, s2.subject, s2.object)]
    if not explain: return dist
    return dist, (s1.article.headline, s1s, s1.quality, s1o, s2s, s2.quality, s2o, subjectdist, dirdist, objectdist, dist)

    
def align(sentences):
    n = max([len(coder) for coder in sentences])
    sentences = [coder[:] + [None] * (n - len(coder)) for coder in sentences]

    # Generate all possible matches, determine best match
    match = None; bestdist = None

    poss = possibilities(sentences)

    for i, p in enumerate(poss):
        dist = 0
        #print "\nPossible world %s" % i
        for arrow in zip(*p): # transpose to get arrowno -> coder
            #print "<%s>" % toolkit.output(arrow, delimiter=' = ', format="%-17s")
            for i, coder in enumerate(arrow):
                for coder2 in arrow[i+1:]:
                    #print "Comparing %s to %s, dist = %1.3f" % (coder, coder2, distance(coder, coder2))
                    dist += distance(coder, coder2)
        #print "Total distance = %s, winner=%s" % (dist, dist > bestdist)
        if bestdist is None or dist < bestdist:
            bestdist = dist
            match = p

    return match


def possibilities(sentences):
    if len(sentences) <= 1: yield [sentences] # don't need to permute the last one, since ordering is relative only
    else:
        head = sentences[0]
        tail = sentences[1:]
        for phead in perms(head):
            if len(tail)==1:
                yield [phead] + tail
            else:
                for possibility in possibilities(tail):
                    yield [phead] + possibility

def perms(str):
    if len(str) <=1:
        yield str
    else:
        for perm in perms(str[1:]):
            for i in range(len(perm)+1):
                yield perm[:i] + str[0:1] + perm[i:]

