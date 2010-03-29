from toolkit import Identity

################ Main rules #################
# All rules starting with getBron_* will be
# traversed in alphabetical order
################

def getBron_1(node):
    if not isVZeg(node.word): return
    debug(getChild(node,"rsubj"))
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
    return word.lemma in ["acknowledge","assert","think","say","state","suggest"]

################# Relations #################

def getSu(node):
    return getChild(node, ("nsubj",))

def getComplOrObj(node):
    return getCompl(node) 

def getCompl(node):
    return getChild(node, ("ccomp",))
    
################# Aux #######################

def getDoel(node, subject):
    frame = SPO("purp", subject=subject)
    pdoel=getChild(node, "mod")
    if hasLemma(pdoel, ["met het oog op", "om","omwille","opdat","zodat","waardoor","teneinde","voor"]): #39404297
        frame.predicate = pdoel
        objecthook = pdoel
    elif hasLemma(pdoel, ["met"]):  #met als isGoal, 39405708
        doelkey = getDescendant(pdoel,pos="N")
        if not isGoal(doelkey): return
        frame.predicate = doelkey
        objecthook = getChild(pdoel, "vc")
    else: return
    frame.object = getDoelObject(objecthook)
    if not frame.isComplete(): frame = None
    return frame

def getDoelObject(pdoel):
    object = getChild(getChild(pdoel,"body"),"body")
    if not object: #met het oog op, met P, 39404297
        object = getChild(pdoel,"obj1")
        debug("1.......",pdoel,object)
    if not object: #zodat, met C, 39405692 
        object = getChild(getChild(pdoel,"body"),"vc")
        debug("2.......",pdoel,object)
    if not object: #zodat, met C, als geen werkwoord onder body, of werkwoord onder "te" 
        object = getChild(pdoel,"body")
        debug("3.......",pdoel,object)
    return object



def doBijzinSODraai(frame):
    frame.subject = getBijzin(frame.subject)
    frame.object = getBijzin(frame.object)
    if isSOdraai(frame.predicate):    #krijgen, ontvangen
        frame.subject, frame.object = frame.object, frame.subject

def getBijzin(node):
    if isBijzin(node): 
        m = getParent(node, "mod")
        if m: return m
    return node

def getSubjectResolveDie(node):
    subject = getChild(node, "su")
    if subject and subject.word.lemma.label in ("die","dat","welke","dewelke"): #39400763, beperkende bijzin: Verhagen (mod) die (su) node
        subject = getParent(subject, "mod")
    return subject

################# Node Finding  #######################

def getTest(e):
    if not e: return lambda x: True
    if type(e) in (list, tuple, set): return e.__contains__
    return e.__eq__

def find(path, rel=None, word=None, lemma=None, pos=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    for n2, r in path:
        if word(n2.word.label) and lemma(n2.word.lemma.label) and pos(n2.word.lemma.pos) and rel(r):
            return n2

def findLast(path, rel=None, word=None, lemma=None, pos=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    result = None
    for n2, r in path:
        if word(n2.word.label) and lemma(n2.word.lemma.label) and pos(n2.word.lemma.pos) and rel(r):
            result = n2
        else:
            return result
    return result
        
def getChild(node, *cond, **kwcond):
    return find(node and node.getRelations(), *cond, **kwcond)

def getParent(node, *cond, **kwcond):
    return find(node and node.getParents(), *cond, **kwcond)
        
def getAncestor(node, *cond, **kwcond):
    return find(getAncestors(node), *cond, **kwcond)

def getRoot(node, *cond, **kwcond):
    return findLast(getAncestors(node), *cond, **kwcond)
    
def getDescendant(node, *cond, **kwcond):              
    return find(getDescendants(node), *cond, **kwcond)   

def getAncestors(node):
    if not node: return
    for n2, rel in node.getParents():
        yield n2, rel
        for n3, rel in getAncestors(n2):
            yield n3, rel

def getDescendants(node):
    if not node: return
    for n2, rel in node.getRelations():
        yield n2, rel
        for n3, rel in getDescendants(n2):
            yield n3, rel

                
def getSibling(node, uprel, *downcond, **kwdowncond):
    return getChild(getParent(node, uprel), *downcond, **kwdowncond)



################# Interface ################

def findBronnen(tree):
    for node in tree.getNodes():
        for name,func in sorted(globals().items()):
            if name.startswith('rule_'):
                frames = func(node)
                if type(frames) not in (list, set, tuple): frames = (frames,)
                for frame in frames:
                    if frame and frame.isComplete():
                        debug("YIELDING===>", frame=frame)
                        yield frame
                    elif frame:
                        debug("Skipping incomplete frame:", frame)


debug_hook = None
def debug(*args, **kargs):
    if not debug_hook: return

    debug_hook(sys._getframe(1).f_code.co_name + ": " + ", ".join(map(str, args) + ["%s=%s" % kv for kv in kargs.iteritems()]))
                
if __name__ == '__main__':
    import dbtoolkit, parsetree
    db = dbtoolkit.amcatDB()
    tree = parsetree.fromDB(db, 121)
    b = Bronnen(tree)
    b.prnt("/home/amcat/www-plain/test.png")
    
    
