_DEFAULT = {'anoko' : 'http://www.content-analysis.org/vocabulary/anoko#',
            'net'   : 'http://www.content-analysis.org/vocabulary/net#',
            'dc'    : 'http://purl.org/dc/elements/1.1/',
            'ont'   : 'http://www.content-analysis.org/vocabulary/ontologies/ont#',
            'k06'   : 'http://www.content-analysis.org/vocabulary/ontologies/k06#',
            'rdfs'  : 'http://www.w3.org/2000/01/rdf-schema#',
            'zu'    : 'http://www.content-analysis.org/vocabulary/ontologies/zurich#',
            'amcat'    : 'http://www.content-analysis.org/vocabulary/amcat#',
            }

class Namespaces:

    def __init__(self, dict = _DEFAULT):
        self.ns = dict

    def NS(self):
        res = "using namespace "
        for k,v in self.ns.items():
            res += "\n  %s = <%s>," % (k, v)
        return res[:-1]

    def deref(self,uri):
        for k,v in self.ns.items():
            uri = uri.replace(v, '%s:' % k)
        return uri
    collapse = deref

    def ref(self,uri):
        for k,v in self.ns.items():
            uri = uri.replace('%s:' % k, v)
        return uri
    expand = ref
                            
