
import toolkit, dot, base64, math, article

def oneimage(arrow): return "Whole set"
def literal(arrow): return arrow.article

class Network:
    def __init__(self):
        self.arrows = []
    def add(self, arrow):
        self.arrows.append(arrow)
    def getdot(self, aggregator = oneimage, relfthreshold = None, absfthreshold = None, includef = False):
        graphs = toolkit.DefaultDict(lambda : toolkit.DefaultDict(list))
        result = {}
        for arrow in self.arrows:
            g = aggregator(arrow)
            graphs[g][arrow.subj, arrow.obj].append(arrow)
        for g,graph in graphs.items():
            d = dot.Graph()
            maxn = len(toolkit.choose(graph.values(), lambda x:len(list(x))))
            for (subj, obj), arrows in graph.items():
                n = len(arrows)
                if relfthreshold and float(n)/maxn < relfthreshold: continue
                if absfthreshold and n < absfthreshold: continue
                q = toolkit.average([arrow.qual for arrow in arrows])

                subj = subj and subj.label
                obj = obj and obj.label
                
                e = d.addEdge(subj, obj)
                lbl = "%+1.1f" % q
                if includef: lbl = "%s %i" % (lbl, n)
                e.label = lbl
                e.weight = n
                e.sign = q
            result[g] = d
        return result
    def judgementExtrapolation(self, ont):
        ideal = ont.nodes[1625]
        media = ont.nodes[1277]
        for r in self.arrows:
            r.judgementExtrapolation(ideal, media)
        

DONTCATEGORIZE= []#["societalgroup"]

class Arrow:
    def __init__(self, subj, obj, qual, type, sentence, src=None, angle=None, predicate=None):
        self.src = src
        self.subj = subj
        self.obj = obj
        self.qual = qual
        self.type = type
        self.angle = angle
        self.predicate = predicate
        self.sentence = sentence
    def posnegneut(self):
        if qual < 0: return -1
        if qual == 0: return 0
        if qual > 0: return 1
    def categorize(self,catid,root=False):
        date = self.sentence.sentence.article.date
        if not self.subj: return # added by jouke
        sur, suc, suo = self.subj.categorize(catid, date)
        if not self.obj: return # added by jouke
        objr, objc, objo = self.obj.categorize(catid, date)
        if root:
            self.subj = sur 
            self.obj = objr
        else:
            if suc: self.subj = suc if (suc.label not in DONTCATEGORIZE) else self.subj
            if objc: self.obj = objc if (objc.label not in DONTCATEGORIZE) else self.obj
        suo = suo or 1
        objo = objo or 1
        self.qual *= suo * objo
    def judgementExtrapolation(self, ideal, media):
        if self.obj == ideal:
            self.obj = self.subj
            self.subj = self.src or media
        
    def getArrowTypeLabel(self):
        return self.sentence.article.db.getValue("select name from net_arrowtypes where arrowtypeid = %i" % self.type)

def fromCodedSentence(codedSentence, ontology):
    s = codedSentence
    #raise Exception(`s.getValue("subject")`)
    #raise Exception(`ontology.nodes`)
    su = ontology.nodes.get(s.getValue("subject"))
    obj = ontology.nodes.get(s.getValue("object"))
    srcid = s.getValue("source")
    src = srcid and ontology.nodes.get(srcid) or None
    qual = s.getValue("quality")
    type = s.getValue("atype")
    return Arrow(su, obj, qual, type, s, src)

if __name__ == '__main__':
    n = Network()
    n.add(Arrow("cda", "pvda", -1, None, 200611))
    n.add(Arrow("cda", "pvda", -1, None, 200610))
    n.add(Arrow("cda", "cda", -1, None, 200611))
    n.add(Arrow("cda", "vvd", 1, None, 200611))
    n.add(Arrow("cda", "vvd", -1, None, 200610))

    print "<html>"
    print "<p><a href='http://www.getfirefox.net/'><i>(Uses object data embedding as per W3C HTML 4.01, might not work using IE)</i></a></p>"
    graphs = n.getdot(aggregator=literal)
    graphs.update(n.getdot())
    for g, graph in graphs.items():
        print "<h1>%s</h1>" % g
        png = graph.getImage(format="png")
        data = base64.b64encode(png)
        print "<object type='image/png' data='data:image/png;base64,%s'></object>" % data
        print "<pre>%s</pre>" % graph.getDot()
    print "</html>"
    
