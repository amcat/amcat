from toolkit import Identity

################ Main rules #################
# All rules starting with getBron_* will be
# traversed in alphabetical order
################

def getBron_1(node):
    if isVZeg(node.word): act="zeg"
    elif isVOrder(node.word): act="order"
    elif isVVraag(node.word): act="vraag"
    else: return
    if isNiet(node): act = "ontken"
    su = getSu(node)
    q = getComplOrObj(node)
    if not (su and q): return
    return su, q, act 

def getBron_N(node):
    if not isNGezegde(node.word): return
    q = getChild(node, "vc")
    hebben = getAncestor(node, "V")
    if not hebben: return
    su = getChild(hebben, "su")
    if not (su and q): return
    return su, q, "zeg"
    

def isNiet(node):
    mod = getChild(node, "mod")
    if not mod: return False
    if mod.word.lemma.label in ["niet"]: return True
    return False
	


def isNGezegde(word):
    return word.lemma.label in ["stelling", "stellingname", "mening", "gedachte"]

def isVZeg(word):
    return word.lemma.label in ["schrijven", "voorstellen", "zeggen", "vind", "zeg", "vinden", "vermoed"]

def isVOrder(word):
    return word.lemma.label in ["beveel", "verordonneer", "adviseer"]
    
def isVVraag(word):
    return word.lemma.label in ["vraag"]


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
    
def getAncestor(node, pos):
    for n2, rel in node.getParents():
      if n2.word.lemma.pos == pos: return n2
      result = getAncestor(n2, pos)
      if result: return result
        

################# Interface ################


class Bron(Identity):
    def __init__(self, tree, key, source, quote, speechAct="zeg"):
        Identity.__init__(self,  tree, key, source, quote, speechAct)
        self.tree = tree
        self.key = key
        self.source = source
        self.quote = quote
        self.speechAct = speechAct

def findBronnen(tree):
    for node in tree.getNodes():
        for name,func in sorted(globals().items()):
            if name.startswith('getBron_'):
                r = func(node)
                if r:
                    su, q, speechAct = r
                    yield Bron(tree, node, su, q, speechAct)
                    break


if __name__ == '__main__':
    import dbtoolkit, parsetree
    db = dbtoolkit.amcatDB()
    tree = parsetree.fromDB(db, 121)
    b = Bronnen(tree)
    b.prnt("/home/amcat/www-plain/test.png")
    
    
