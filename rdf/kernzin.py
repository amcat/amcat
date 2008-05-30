import namespace, dbtoolkit, ontology, rdftoolkit, toolkit

def fromSesame(rdfdb = None, sqldb = None, batches = None, where = None):

    if not rdfdb: rdfdb = rdftoolkit.anokoRDF()
    if not sqldb: sqldb = dbtoolkit.anokoDB()
    
    SeRQL = """
    SELECT An, Rel, X, Unit, Article FROM
    {An} Rel {X};
         dc:subject {Unit} anoko:InArticle {Article} anoko:InBatch {Batch}
    """

    if not where: where = []
    elif toolkit.isString(where): where = [where]
    if batches: where.append(' OR '.join(['(Batch = "%s"^^xsd:int)' % b for b in batches]))

    if where: SeRQL += ' WHERE (%s)' % ')\nAND ('.join(where)
    
    
    data = {} # an_url : Kernzin

    print "Getting results..."

    results = rdfdb.execute(SeRQL)

    print "Creating internal data structure"

    for an, rel, x, unit, article in results:
        if an not in data:
            aid = int(article.split("-")[-1])
            article = sqldb.article(aid)
            unit = tuple(int(x) for x in unit.split("-")[-2:])
            data[an] = Kernzin(an, article, unit, rdfdb)
        data[an].setRelation(rel, x)

    for id, kernzin in data.items():
        if (kernzin.subject is None or kernzin.object is None or kernzin.quality is None):
            del(data[id])
    
    print "kernzin.fromSesame done" 

    return data.values()
        
PROPERTIES = {"net:Subject" : "subject",
              "net:Object" : "object",
              "net:Source" : "source",
              "net:Predicate" : "predicate",
              "net:Quality" : "quality",
              "net:ArrowType" : "arrowtype",
              "net:Angle" : "angle",
              "dc:author" : "coder",              
              }
              
DISPLAYFIELDS = "source","subject","predicate","quality","arrowtype","object"

def displayHeader():
    return DISPLAYFIELDS



class Kernzin:

    def __init__(self, url,  article, unit, rdfdb):
        self.url = url
        self.article = article
        self.unit = unit
        self.rdfdb = rdfdb

        self.source = None
        self.subject = None
        self.predicate = None
        self.quality = None
        self.arrowtype = None
        self.object = None
        self.angle = None

#        self.persgenre = None
#        self.perswie = None
#        self.perswat = None
#        self.perswaar = None
#        self.perswanneer = None
#        self.perswaarover = None
                                        

        
        
        self.coder = None

    def displayFields(self, links=False):
        res = [self.__dict__.get(x, None) for x in DISPLAYFIELDS]
        if links:
            for i, val in enumerate(res):
                if type(val) == ontology.concepttype:
                    res[i] = rdftoolkit.link(val.url, val.label())
        return res

    def setRelation(self, url, value):
        global PROPERTIES
        url = self.rdfdb.nscollapse(url)
        prop = PROPERTIES.get(url, None)
        if not prop:
            return

        if prop not in self.__dict__: raise Exception("Uknown property: %s" % prop)
        self.__dict__[prop] = self._transform(prop, value)

    def _transform(self, prop, value):
        if prop == 'coder': value = value.split("-")[-1]
        if prop in ('subject','object','source','angle'): value = self.rdfdb.concept(value)
        if prop == 'quality': value = float(int(value)) / 100
        return value

    def __str__(self, meta = False):
        res = "["
        if meta:
            res += "%s;%s | " % (self.article.id, self.coder)
        return res + "%s'%s' / %s %s / '%s']" % (self.source and "'%s': " % self.source or "", self.subject, self.arrowtype, self.quality, self.object)
    str = __str__


if __name__ == '__main__':
    fromSesame()
