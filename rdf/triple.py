import dbtoolkit, toolkit, re, sys

def clean(s, xml=False):
    if not s: return None
    if type(s) == int: return s
    s = s.replace('"', "'")
    s = toolkit.clean(s, level=1)
    if xml: s=s.replace('&', "&amp;")
    
    return s

class Triple(object):
    def __init__(self, subject, predicate, object, literal = False):
        self.subject = subject
        self.predicate = predicate
        self.object= object
        self.literal = literal
    def n3(self):
        if self.literal:
            o = '"%s"' % clean(self.object)
        else:
            o = self.object

        return "%s %s %s." % (self.subject, self.predicate, o)
    def rdfxml(self):
        if self.literal:
            value = clean(self.object, xml=True)
            return '''<rdf:Description rdf:about="%s"><%s>%s</%s></rdf:Description>''' % (self.subject, self.predicate, value, self.predicate)
        else:
            return '''<rdf:Description rdf:about="%s"><%s rdf:resource="%s" /></rdf:Description>''' % (self.subject, self.predicate, self.object)
    def __hash__(self):
        return hash((self.subject, self.object, self.predicate, self.literal))
    def __eq__(self, other):
        if type(other) <> Triple: return False
        return (self.subject, self.object, self.predicate, self.literal) == (other.subject, other.object, other.predicate, other.literal)
    def __str__(self):
        return "%s --(%s)--> %s" % (self.subject, self.predicate, self.object)
    def __repr__(self):
        return "%sTriple(%r, %r, %r)" % (self.literal and "L" or "", self.subject, self.predicate, self.object)

class RDFXMLWriter:
    def __init__(self, out=sys.stdout):
        self.out = out
    def start(self):
        print >>self.out, '''<?xml version="1.0"?>\n\n<rdf:RDF
        xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
        xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
        xmlns:a="http://www.content-analysis.org/vocabulary/alpino#" >\n\n'''
    def serialize(self, triples):
        for triple in triples:
            print >>self.out, triple.rdfxml()
    def end(self):
        print >>self.out, "\n</rdf:RDF>"

class N3Writer:
    def __init__(self, out=sys.stdout):
        self.out = out
    def start(self):
        print >>self.out, """@prefix a: <http://www.content-analysis.org/vocabulary/alpino#>.
                 @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.\n\n"""
    def serialize(self, tripleS):
        for triple in triples:
            print >>self.out, triples.n3()
    def end(self):
        pass

def LTriple(subject, predicate, object):
    return Triple(subject, predicate, object, literal = True)

