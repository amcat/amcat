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
            maxn = len(toolkit.choose(graph.values(), len))
            totn = sum([len(x) for x in graph.values()])
            for (subj, obj), arrows in graph.items():
                n = len(arrows)
                if relfthreshold and float(n)/totn < relfthreshold: continue
                if absfthreshold and n < absfthreshold: continue
                q = sum(arrow.qual for arrow in arrows)
                q = float(q) / n

                subj = subj.label
                obj = obj.label
                
                e = d.addEdge(subj, obj)
                lbl = "%+1.1f" % q
                if includef: lbl = "%s %i" % (lbl, n)
                e.setlabel(lbl)
                e.setcolor(.67-.33*q,1,.5)
                if maxn > 5: n = math.sqrt(float(n) / maxn * 20)
                e.setlinewidth(n)
                
            result[g] = d
        return result
                
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
    def getArrowTypeLabel(self):
        return self.sentence.article.db.getValue("select name from net_arrowtypes where arrowtypeid = %i" % self.type)

def fromCodedSentence(codedSentence, ontology):
    s = codedSentence
    su = ontology.nodes[s.getValue("subject")]
    obj = ontology.nodes[s.getValue("object")]
    srcid = s.getValue("source")
    src = srcid and ontology.nodes[srcid] or None
    qual = s.getValue("quality")
    type = s.getValue("atype")
    sentence = s.sentence
    return Arrow(su, obj, qual, type, sentence, src)

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
    
