import pySesameDB, namespace, ontology, labels,toolkit, urllib

_debug = toolkit.Debug('dbtoolkit',2)

class anokoRDF:

    def __init__(self, reponame = 'anoko'):
        self.ns        = anokoNS()
        _debug(2,"Connecting to sesame server")
        self.db        = pySesameDB.connect('http://localhost:8088/sesame', 'wouter', 'maanbrem', reponame, namespaces = self.ns)
        self._labels   = None
        self._ontology = None


    def label(self, url):
        if toolkit.isDate(url):
            return toolkit.writeDate(url)
        if type(url) == int:
            return "%i" % url
        if toolkit.isFloat(url):
            return "%1.1f" % url
        if not ":" in url:
            return url
        return self.getLabels().lookup(url)

    def getLabels(self):
        if not self._labels:
            _debug(3,"Getting labels")
            self._labels = labels.Labels(self)
        return self._labels
    
    def nscollapse(self, url):
        if isURI(url):
            return self.ns.collapse(url)
        else:
            return url
        
    def nsexpand(self, url):
        return self.ns.expand(url)

    def ontology(self):
        if not self._ontology:
            _debug(3,"Getting Ontology")
            self._ontology = ontology.Ontology(self)
        return self._ontology

    def concept(self, url):
        return self.ontology().concept(url)

    def execute(self, SeRQL):
        return self.db.execute(SeRQL)

_ANOKONS = None
def anokoNS():
    global _ANOKONS
    if _ANOKONS is None: _ANOKONS = namespace.Namespaces()
    return namespace.Namespaces()

def link(uri, text):
    uri = anokoNS().expand(uri)
    uri = urllib.quote_plus('<%s>' % uri)
    return '<a href="http://localhost:8088/sesame/explorer/show.jsp?repository=anoko&value=%s">%s</a>' % (uri, text)

def isURI(obj):
    return pySesameDB.isURI(obj)
