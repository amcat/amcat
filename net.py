import toolkit, dot, base64, math, article, copy, collections, functools, codingjob

LBL_Q, LBL_W, LBL_D, LBL_A, LBL_V = 1,2,4,8,16
LBL_3 = LBL_Q | LBL_W | LBL_V

def PER_ARTICLE(r): return r.getArticle()
def PER_SOURCE(r): return r.src
def COMBINE(x,y): return lambda r: (x(r), y(r))
PER_ARTICLE_SOURCE = COMBINE(PER_ARTICLE, PER_SOURCE)
def NOSOURCE(r): return not r.src

def lbl(node):
    if node is None: return node
    try:
        return node.getLabel()
    except AttributeError:
        return node

    
debug = toolkit.Debug("net.py", -1)
    
class Dataset(object):
    def __init__(self):
        self.arrows = []
    def add(self, arrow):
        debug(3, arrow)
        self.arrows.append(arrow)
    def getChains(self, chainunit=PER_ARTICLE, splitter=None, extrapolate=False, stripSources=False):
        networks = collections.defaultdict(Network)
        data = self.getLinks(splitter=chainunit).items()
        debug(1, "Calculating chains per article (%i articles)" % len(data))
        for i, (context, network) in enumerate(data):
            debug(2, "Calculating chains for article %i/%i %s" % (i+1, len(data), context))
            # chain source nets, extrapolate to main net, chain main net, distribute
            sourcenets = []
            for src, srcnet in distribute(network.arrows, splitter=PER_SOURCE).items():
                debug(3, "Source %s" % src)
                srcnet = chain(srcnet, context=context)
                sourcenets.append(srcnet)
            mainnet = filter(network.arrows, NOSOURCE)
            #toolkit.warn("Main net for %s: %s" % (context, mainnet.arrows))
            if extrapolate:
                doExtrapolate(mainnet, sourcenets)
            mainnet = chain(mainnet, context=context)
            distribute(mainnet.arrows, networks, splitter=splitter)
            for sourcenet in sourcenets:
                distribute(sourcenet.arrows, networks, splitter=splitter, stripSources=stripSources)
        debug(1, "Returning splits(%r, %r)"% (networks, splitter))
        return splits(networks, splitter)
        
    def getLinks(self, *args, **kargs):
        return bundleNetworks(self.getArrows(*args, **kargs))
    def getBundles(self, *args, **kargs):
        return bundleNetworks(self.getChains(*args, **kargs))
    def getArrows(self, splitter=None):
        return distribute(self.arrows, splitter=splitter)

def bundleNetworks(n):
    if type(n) == Network: return bundle(n)
    result = {}        
    for id, network in n.items():
        result[id] = bundle(network)
    return result
    
    
def splits(networks, splitter):
    return networks if splitter else networks[True]

def filter(arrows, filter):
    n = Network()
    for r in arrows:
        if filter(r): n.add(r)
    return n
                                   
                                 
def distribute(arrows, networks=None, splitter=None, stripSources=False):
    if networks is None: networks = {}
    for r in arrows:
        v = splitter(r) if splitter else True 
        if v:
            if v not in networks: networks[v] = Network()
            if stripSources and r.src:
                if r.obj.id in IDEAL: continue
                r.src = None
            networks[v].add(r)
    return splits(networks, splitter)
                  
              
    
class Network(object):
    def __init__(self):
        self.arrows = []
        self.viscache = None
    def add(self, arrow):
        self.arrows.append(arrow)
        self.viscache = None
    def getdot(self, **kargs):
        d = dot.Graph()
        self.addEdges(d, **kargs)
        return d
    def addEdges(self, graph, relfthreshold = None, absfthreshold = None, includef = False, label=None, dropsource=False, wfmt="%1.2f"):
        if label is None: label = LBL_Q | LBL_W if includef else LBL_Q
        result = []
        if relfthreshold:
            som = sum(arrow.weight for arrow in self.arrows)
            absfthreshold = som * relfthreshold
        for arrow in self.arrows:
            w = arrow.weight
            if absfthreshold and w < absfthreshold: continue
            q = arrow.qual

            src = lbl(arrow.src)
            subj = lbl(arrow.subj)
            obj = lbl(arrow.obj)

            l = []
            if LBL_Q & label: l += ["%+1.1f" % arrow.qual]
            if LBL_W & label: l += [wfmt % w]
            if LBL_D & label: l += ["%1.2f" % arrow.divergence]
            if LBL_A & label: l += ["%1.2f" % arrow.ambivalence]
            if LBL_V & label: l += ["%1.2f" % arrow.var()]
            if src and dropsource: continue
            e = graph.addEdge(subj, obj, graph=src)
            e.weight = w
            e.label = " ".join(l)
            e.sign = q
            result.append(e)
        return result
    
    def judgementExtrapolation(self, ont):
        # deprecated
        ideal = ont.nodes[1625]
        media = ont.nodes[1277]
        for r in self.arrows:
            r.judgementExtrapolation(ideal, media)

    def outdegree(self, node):
        if self.viscache is None:
            self.viscache = collections.defaultdict(float)
            for r in self.arrows:
                self.viscache[r.subj] += r.weight
        return self.viscache[node]
    def relweight(self, arrow):
        #self.viscache = None
        if arrow.weight > self.outdegree(arrow.subj): raise Exception()
        return arrow.weight / self.outdegree(arrow.subj)
        

DONTCATEGORIZE= []#["societalgroup"]

class Arrow(object):
    def __init__(self, subj, obj, qual, type, context, angle=None, predicate=None, weight=1, divergence=0, ambivalence=0, src=None):
        self.subj = subj
        self.obj = obj
        self.src = src
        
        self.qual = qual
        self.type = type
        self.weight = weight
        self.divergence = divergence
        self.ambivalence = ambivalence
        if (divergence + ambivalence) > 1: raise Exception("%1.2f %1.2f %1.2f %r" % (divergence, ambivalence, divergence+ambivalence, self))

        self.angle = angle
        self.predicate = predicate
        self.context = context
    def posnegneut(self):
        if qual < 0: return -1
        if qual == 0: return 0
        if qual > 0: return 1
    def categorize(self,catid,depth=1):
        date = self.getArticle().date
        if not (self.subj and self.obj):
            raise Exception
        suc, suo = self.subj.categorize(catid, date=date, depth=depth)
        objc, objo = self.obj.categorize(catid, date=date, depth=depth)
        if suc is None: raise Exception(self.subj.id)
        if objc is None: raise Exception(self.obj.id)
        self.subj = suc or self.subj#if (suc and suc.getLabel() not in DONTCATEGORIZE) else self.subj
        self.obj = objc or self.obj# if (objc and objc.getLabel() not in DONTCATEGORIZE) else self.obj
        suo = suo or 1
        objo = objo or 1
        self.qual *= suo * objo
    def judgementExtrapolation(self, ideal, media):
        #deprecated
        if self.obj == ideal:
            self.obj = self.subj
            self.subj = self.src or media
    def var(self):
        return self.divergence + self.ambivalence

    def __repr__(self):
        return "%s:%s-%s>%s w=%1.2f>" % (self.src, self.subj, self.qual>0 and "+" or "-", self.obj, self.weight)
        
    def getArrowTypeLabel(self):
        return self.sentence.article.db.getValue("select name from net_arrowtypes where arrowtypeid = %i" % self.type)

    def getSentence(self):
        c = self.context
        if type(c) == codingjob.CodedSentence: return c.sentence
        if type(c) == article.Sentence: return c
        raise Exception("Cannot get sentence from context %s : %s" % (type(c), c))

    def getCodedSentence(self):
        c = self.context
        if type(c) == codingjob.CodedSentence: return c
        raise Exception("Cannot get CodedSentence from context %s : %s" % (type(c), c))

    def getCodedArticle(self):
        c = self.context
        if type(c) == codingjob.CodedSentence: return c.ca
        if type(c) == codingjob.CodedArticle: return c
        raise Exception("Cannot get CodedArticle from context %s : %s" % (type(c), c))

    
    def getArticle(self):
        c = self.context
        if type(c) == article.Article: return c
        if type(c) == codingjob.CodedSentence: return c.ca.article
        # hack!
        if type(c) == str: return c
        return c.article
        

def fromCodedSentence(codedSentence, ontology):
    s = codedSentence
    #raise Exception(`s.getValue("subject")`)
    #raise Exception(`ontology.nodes`)
    su = ontology.nodes.get(s.getValue("subject"))
    obj = ontology.nodes.get(s.getValue("object"))
    srcid = s.getValue("source")
    if s.getValue("predicate")=="promised":
        debug(-1, str(srcid))
        debug(-1, str(ontology.nodes.get(srcid)))
    src = srcid and ontology.nodes.get(srcid) or None
    qual = s.getValue("quality")
    atype = s.getValue("arrowtype")
    return Arrow(su, obj, qual, type=atype, context=s, src=src)

IDEAL = [1625, 200, 14361,14364,14391,14394,14396,14397,14399,14402,14404,14405,14407]
    
def doExtrapolate(main, sources, ideal=IDEAL):
    for source in sources:
        for r in source.arrows:
            if r.src and r.obj.id in ideal:
                main.add(Arrow(r.src, r.subj, r.qual, "AFF", r.context, weight=r.weight, divergence=r.divergence, ambivalence=r.ambivalence))
    return main
    

def bundle(network, ignoreSource=False):
    links = collections.defaultdict(list)
    for r in network.arrows:
        links[r.src, r.subj, r.obj].append(r)
    n = Network()
    for (z, x,y), arrows in links.items():
        w = sum(r.weight for r in arrows)
        q = sum(r.qual * r.weight for r in arrows) / w
        d = sum(r.weight * (r.qual - q)**2 for r in arrows ) / w
        a = sum(r.weight * r.ambivalence for r in arrows) / w
        n.add(Arrow(x, y, q, "ASS", r.context, src=z, weight=w, divergence=d, ambivalence=a))
    return n

#def netsum(i, j):
#    w = i.weight + j.weight
#    q = (i.qual * i.weight + j.qual * j.weight) / w
#    a = (i.var() * i.weight + j.var() * j.weight) / w
#    d = (i.qual**2 * i.weight) / w -

def chain(network, context, threshold=0):
    # set up links dict for speed
    links = collections.defaultdict(list)
    for edge in network.arrows:
        links[edge.subj].append(edge)


    # create chains as {start, [[([arrow1, arrow2, ...], relweight), ...], ...]}
    chains = collections.defaultdict(list)
    for node in links.keys()[:]:
        current = [([], 1)]
        while current:
            new = []
            for (path, w) in current:
                nodes = set([e.subj for e in path]) |set([e.obj for e in path]) 
                b = path[-1].obj if path else node
                if b in chains:
                    for (path3, w3) in chains[b]:
                        w2 = w * w3
                        if w2 < threshold: continue
                        ok = True
                        for edge in path3:
                            if edge.obj in nodes: 
                                ok = False
                                break
                        if not ok: continue
                        
                        path2 = path[:] + path3[:]
                        chains[path2[0].subj].append((path2, w2))
                else:
                    if b in links:
                        for edge in links[b]:
                            if edge.obj in nodes: continue
                            path2 = path[:] + [edge]
                            w2 = w * network.relweight(edge)
                            if w2 < threshold: continue
                            chains[path2[0].subj].append((path2, w2))
                            new.append((path2, w2))
            current = new


    # create chain 'arrows'
    result = Network()        
    for start, chainseq in chains.items():
        for chain, w in chainseq:
            try:
                r = reduce(functools.partial(netproduct, network), chain)
            except Exception, e: 
                toolkit.warn(chain)
                raise e
            # if len(chain)==1, weight is still absolute instead of relative!
            if len(chain) > 1:
                r.weight *= network.outdegree(start)
            r.context = context
            result.add(r)
    return result

def netproduct(network, i, j):
    if i.src <> j.src: raise Exception("Cannot chain links with different sources!")
    w = network.relweight(i) * network.relweight(j)
    q = i.qual * j.qual
    d = 0.0
    
    a = ((i.var() + i.qual**2) * (j.var() + j.qual**2)) - (i.qual**2 * j.qual**2)
    if a>1.0 and a<1.01: a = 1.0
    result = Arrow(i.subj, j.obj, q, "ASS", None, src=i.src, weight=w, ambivalence=a, divergence=d)
    return result

class Sent:
    def __init__(self, art):
        self.article = art

def fromCodingjobs(db, codingjobids, ont=None):
    if not ont:
        import ont2
        ont = ont2.fromDB(db)
    d = Dataset()
    for cs in codingjob.getCodedSentencesFromCodingjobIds(db, codingjobids):
        d.add(fromCodedSentence(cs, ont))
    return d

def networkFromCodingjobs(db, codingjobids, ont=None):
    return fromCodingjobs(db, codingjobids, ont).getArrows()
                    
if __name__ == '__main__':
    import dbtoolkit, ont2, sys
    debug = toolkit.Debug("net",2)
    db = dbtoolkit.anokoDB()
    ont = ont2.fromDB(db)
    jobs = [codingjob.getCodingJob(db, x) for x in [1836]]
    d = Dataset()
    for job in jobs:
        for s in list(job.sets):
            for ca in s.articles:
                s = ca.__str__()
                if u"voor zich winnen" not in ca.__str__(): continue
                if u"Wendy" not in ca.__str__(): continue
                for cs in ca.sentences:
                    r = fromCodedSentence(cs, ont)
                    print r.subj, r.obj,
                    r.categorize(101)
                    print r.subj, r.obj
                    d.add(r)

    sys.exit(1)
    l = d.getLinks()
    b = d.getBundles()
    ll = d.getLinks(splitter=PER_ARTICLE)
    bb = d.getBundles(splitter=PER_ARTICLE)
    data =[("Links total", l)]
    for a in ll:
        data += [(a, ll[a])]
        data += [("Bundles:", bb[a])]
    data += [("Bundles total", b)]

    print "<html>"
    print "<p><a href='http://www.getfirefox.net/'><i>(Uses object data embedding as per W3C HTML 4.01, might not work using IE)</i></a></p>"
    
    for l, network in data:
        print "<h1>%s</h1>" % (l,)
        if not network: continue
        print "<table border='1'><tr><th>Subject</th><th>Object</th><th>Q</th><th>W</th><th>W'</th></th><th>D</th><th>A</th><th>V</th></tr>"
        data = []
        for r in network.arrows:
            data.append([r.subj, r.obj, r.qual, r.weight, network.relweight(r), r.divergence, r.ambivalence, r.var()])
        data.sort()
        for d in data:
            print "<tr>%s</tr>" % "".join("<td>%s</td>" % x for x in d)
        print "</table>"
        graph = network.getdot(label=LBL_3)
        graph.normalizeWeights()
        png = graph.getImage(format="png")
        data = base64.b64encode(png)
        print "<object type='image/png' data='data:image/png;base64,%s'></object>" % data
        print "<!-- %s -->" % graph.getDot()
    print "</html>"
    
