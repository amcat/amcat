import cachable
import toolkit

from article import Article
from sentence import Sentence
from codingjob import Codingjob, CodedArticle, CodingjobSet, CodedSentence

import rdflib

NS_AMCAT = rdflib.Namespace(u"http://content-analysis.org/rdf/data/amcat/")
NS_DC = rdflib.Namespace(u"http://purl.org/dc/elements/1.1/")

CLASS2URIPART = {}
CLASSPROP2PREDICATE = {}
PROP2PREDICATE = {
    "source" : NS_DC["publisher"],
    "date" : NS_DC["date"],
    "id" : NS_DC["reference"],
    "headline" : NS_DC["title"]
    }

def getRDF(subject, recurse=False, included=None):
    if not included: included = set()
    if subject in included: return
    included.add(subject)
    if type(recurse) not in (bool, set, list, tuple): recurse=(recurse,)
    subjectNode = getNode(subject)
    for prop in subject._getPropertyNames():
        object = subject.__getattribute__(prop)
        if not toolkit.isIterable(object): object = (object,)
        for o in object:
            objectNode=getNode(o)
            predicate = getPredicate(prop, subject, o)
            if objectNode and predicate:
                yield (subjectNode, predicate, objectNode)
                if recurse == True or type(o) in recurse :
                    for s,p,o in getRDF(o, recurse, included):
                        yield s,p,o

def getPredicate(prop, subject, object):
    pred = CLASSPROP2PREDICATE.get((subject, prop))
    if not pred: pred= PROP2PREDICATE.get(prop)
    if not pred: pred= NS_AMCAT[prop]
    return pred
                
                
def getNode(object):
    if isinstance(object, cachable.Cachable):
        classname = CLASS2URIPART.get(object.__class__, object.__class__.__name__)
        if not classname: return None
        id = "%s_%s" % (classname, object.id)
        return NS_AMCAT[id]
    else:
        if type(object) == unicode:
            object = object.encode('ascii', 'replace').decode('ascii')
        elif type(object) == str:
            object = object.decode('latin-1')
        else:
            object = str(object).decode('latin-1')
        return rdflib.Literal(object)
    
if __name__ == '__main__':
    import dbtoolkit, article
    db = dbtoolkit.amcatDB()
    cj = Codingjob(db, 2572)
    for s,p,o in getRDF(cj, recurse=[CodingjobSet, CodedArticle]):
        print s,p,o
