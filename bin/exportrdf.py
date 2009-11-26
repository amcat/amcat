import rdflib, toolkit, re

NS_ONT = rdflib.Namespace(u"http://content-analysis.org/rdf/voca/ont/")
NS_NET = rdflib.Namespace(u"http://content-analysis.org/rdf/voca/net/")
NS_AMCAT = rdflib.Namespace(u"http://content-analysis.org/rdf/data/amcat/")
NS_SKOS = rdflib.Namespace(u"http://www.w3.org/2004/02/skos/core#")
NS_RDFS = rdflib.Namespace(u"http://www.w3.org/2000/01/rdf-schema#")
NS_RDF = rdflib.Namespace(u"http://www.w3.org/1999/02/22-rdf-syntax-ns#")
NS_DC = rdflib.Namespace(u"http://purl.org/dc/elements/1.1/")

SKOS_PREFLABEL = NS_SKOS[u"prefLabel"]
SKOS_ALTLABEL = NS_SKOS[u"altLabel"]
SKOS_BROADER = NS_SKOS[u"broader"]

RDFS_SUBPROP = NS_RDFS["subPropertyOf"]
RDF_TYPE = NS_RDF["type"]

DC_REFERENCE = NS_DC["Reference"]
DC_SOURCE = NS_DC["Source"]
DC_PUBLISHER = NS_DC["Publisher"]
DC_TITLE = NS_DC["Title"]
DC_DATE = NS_DC["Title"]


PREFLANG = 1

def ont2skos(ont, graph=None, subprops=True):
    langids = dict(ont.db.doQuery("select languageid, label from languages"))
    if graph is None:
        graph = rdflib.ConjunctiveGraph()
    classes = set()
    for node in ont.nodes.values():
        rn = rdfnode(node)
        langs = node.labels.keys()
        preflang = PREFLANG if (PREFLANG in langs) else min(langs)
        for lang, label in node.labels.items():
            pred = SKOS_PREFLABEL if lang == preflang else SKOS_ALTLABEL
            label = toolkit.stripAccents(label).encode("ascii","replace").decode("ascii")
            label = rdflib.Literal(label, lang = langids[lang])
            graph.add((rn, pred, label))
            
        for cls, (parent, omklap) in node.parents.items():
            if parent:
                n2 = rdfnode(parent)
                cls = skoslink(cls) if subprops else SKOS_BROADER
                classes.add(cls)
                graph.add((rn, cls, n2))
    if subprops:
        for cls in classes:
            graph.add((cls, RDFS_SUBPROP, SKOS_BROADER))
                
    return graph
            
def skoslink(cls):
    l = cls.label
    l = l.replace(" ","_")
    l = re.sub("\W","", l)
    return NS_ONT[l]
            
def rdfnode(n):
    return NS_ONT[unicode(n.id)]

def posneg(arrow):
    return NS_NET[{-1:u"neg", 0:u"neut", 1:u"pos"}[cmp(arrow.qual, 0)]]
    

def net2RDF(network, predfunc=posneg, graph=None):
    if graph is None:
        graph = rdflib.ConjunctiveGraph()
    
    for arrow in network.arrows:
        graph.add((rdfnode(arrow.subj), predfunc(arrow), rdfnode(arrow.obj)))
    return graph

DC_REFERENCE = NS_DC["Reference"]
DC_SOURCE = NS_DC["Source"]
DC_PUBLISHER = NS_DC["Publisher"]
DC_TITLE = NS_DC["Title"]
DC_DATE = NS_DC["Date"]

def RDFMetadata(unit, graph):
        
    if type(unit) == codingjob.CodedSentence:
        node = NS_AMCAT["codedsentence-%i" % unit.id]
        art = unit.ca.article
    else:
        node = NS_AMCAT["codedarticle-%i" % unit.id]
        art = unit.article
    artnode = NS_AMCAT["article-%i" % art.id]
    
    graph.add((node, DC_REFERENCE, rdflib.Literal(unit.id)))
    graph.add((node, DC_SOURCE, artnode))
    graph.add((artnode, DC_REFERENCE, rdflib.Literal(art.id)))
    if art.headline: graph.add((artnode, DC_TITLE, rdflib.Literal(art.headline)))
    if art.date: graph.add((artnode, DC_DATE, rdflib.Literal(art.date)))
    if art.source: graph.add((artnode, DC_PUBLISHER, rdflib.Literal(art.source)))
    return node
    

def getSchema(unit):
    if type(unit) == codingjob.CodedSentence:
        return unit.ca.set.job.unitSchema
    else:
        return unit.set.job.articleSchema
     
def units2RDF(units, graph=None):
    if graph is None:
        graph = rdflib.ConjunctiveGraph()
    for unit in units:
        an = RDFMetadata(unit, graph)
        graph.add((an, RDF_TYPE, NS_NET["annotation"]))
        schema  = getSchema(unit)
        for field in schema.fields:
            pred = NS_AMCAT["schemafield-%s" % field.fieldname]
            val = unit.getValue(field)
            if val is None: continue
            val = field.deserialize(val)
            if type(val) == ont2.Object:
                obj = rdfnode(val)
            else:
                obj = rdflib.Literal(val)
            graph.add((an, pred, obj))
        
FORMATS = ('n3','xml')

if __name__ == '__main__':
    import dbtoolkit, net, ont2, sys, codingjob, toolkit

    if len(sys.argv) < 3:
        print "Usage: python netrdf.py WHAT [FORMAT] CODINGJOBS\n\nWHAT can be sentence, article, or network."
        sys.exit()
    what = sys.argv[1]
    if what not in ("sentence", "article", "network", "both"):
        print "Usage: python netrdf.py WHAT [FORMAT] CODINGJOBS\n\nWHAT can be sentence, article, both, or network."
        sys.exit()

    format = sys.argv[2]
    ids = sys.argv[3:]

    if format not in FORMATS:
        ids += [format]
        format = 'n3'
        
    ids = map(int, ids)

    toolkit.warn("Setting up...")
    db = dbtoolkit.amcatDB()
    ont = ont2.fromDB(db)

    graph = rdflib.ConjunctiveGraph()
    toolkit.warn("Writing ontology")
    ont2skos(ont, graph, subprops=False)

    if what == "network":
        toolkit.warn("Getting data")
        n = net.networkFromCodingjobs(db, ids, ont)
        toolkit.warn("Creating RDF")
        net2RDF(n, graph=graph)
    else:
        toolkit.warn("Getting data")
        units = []
        if what <> "sentence":
            units += list(codingjob.getCodedArticlesFromCodingjobIds(db, ids))
        if what <> "article":
            units += list(codingjob.getCodedSentencesFromCodingjobIds(db, ids))
        toolkit.warn("Creating RDF")
        units2RDF(units, graph=graph)
              
  
    toolkit.warn("Printing RDF")
    print graph.serialize(format=format)

        

