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
    return su, q

def isVZeg(word):
    return word.lemma.label in ["schrijven", "voorstellen", "zeggen"]

################# Relations #################

def getSu(node):
    return getChild(node, ("su",))

def getComplOrObj(node):
    return getCompl(node) or getObj(node)

def getCompl(node):
    return getChild(node, ("vc",))
def getObj(node):
    return getChild(node, ("obj1",))
    
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
                    su, q = r
                    yield Bron(tree, node, su, q)
                    break


if __name__ == '__main__':
    import dbtoolkit, parsetree
    db = dbtoolkit.amcatDB()
    tree = parsetree.fromDB(db, 121)
    b = Bronnen(tree)
    b.prnt("/home/amcat/www-plain/test.png")
    
    
