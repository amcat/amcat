from toolkit import Identity

################ Main rules #################
# All rules starting with getBron_* will be
# traversed in alphabetical order
################

def getBron_1(node):
    if not isVZeg(node.word): return
    su = getSu(node)
    q = getComplOrObj(node)
    if not (su and q): return
    return su, node, q

def getBron_according(node):
    key= getChild(node, "prep")
    if not key or not key.word.lemma == "accord": return
    to = getChild(key, "dep")
    if not to or not to.word.lemma == "to": return
    su = getChild(to, "pobj")
    if not su: return
    return su, key, node

def isVZeg(word):
    return word.lemma in ["think","say"]

################# Relations #################

def getSu(node):
    return getChild(node, ("nsubj",))

def getComplOrObj(node):
    return getCompl(node) 

def getCompl(node):
    return getChild(node, ("ccomp",))
    
################# Aux #######################

def getChild(node, rel):
    if type(rel) not in (list, tuple, set):
        rel = (rel,)
    for n, r in node.getRelations():
        if r in rel:
            return n


################# Interface ################


class Bron(Identity):
    def __init__(self, tree, key, source, quote):
        Identity.__init__(self,  tree, key, source, quote)
        self.tree = tree
        self.key = key
        self.source = source
        self.quote = quote

def findBronnen(tree):
    for node in tree.getNodes():
        for name,func in sorted(globals().items()):
            if name.startswith('getBron_'):
                r = func(node)
                if r:
                    su, key, q = r
                    yield Bron(tree, key, su, q)
                    break


