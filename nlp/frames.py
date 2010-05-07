from toolkit import Identity
import toolkit
import parsetree
import sys

############# INTERFACE ETC. ################

LEMMA_SQL = """select distinct l.lemmaid from words_lemmata l inner join words_words w on l.lemmaid = w.lemmaid inner join words_strings s on s.stringid = w.stringid where string in (%s)"""
    
class Rule(object):
    def __init__(self, identifier, verbose=False):
        self.identifier = identifier
        self.verbose = verbose
    def debug(self, *args, **kargs):
        if self.verbose: self.identifier.debug(*args, **kargs)
class DeclarativeRule(Rule):
    def __init__(self, identifier, frame, condition=None, postprocess=None, verbose=False, name=None, **roles):
        Rule.__init__(self, identifier, verbose)
        self.frame = frame
        self.condition = condition
        self.postprocess = postprocess
        self.roles = roles
        self.name = name
    def getFrame(self, node):
        return self.frame(name=self.name)
    def matches(self, node):
        frame = self.getFrame(node)
        if not frame: return
        for role, pattern in self.roles.iteritems():
            n = pattern.getNode(node)
            if n: frame.__dict__[role] = n
        frame = self.doPostProcess(frame)
        frame = self.doCheck(frame)
        return frame

    def doPostProcess(self, frame):
        if self.postprocess: frame = self.postprocess(self.identifier, frame)
        return frame
      
    def doCheck(self, frame):
        if self.condition:
            conds = self.condition
            if callable(conds): conds = [conds]
            for cond in conds:
                if not cond(self, frame):
                    return None
        return frame
          
class FunctionRule(object):
    def __init__(self, db, function):
        Rule.__init__(self, db)
        self.function = function
    def matches(self, node):
        return self.function(node)

    
    
class Pattern(object):
    def __init__(self, func=None):
        self.func = func
    def getNode(self, node):
        return self.func(node)
class Conditional(Pattern):
    def __init__(self, func, *cond, **kwcond):
        self.func = func
        self.cond = cond
        self.kwcond = kwcond
    def getNode(self, node):
        return self.func(node, *self.cond, **self.kwcond)
class Child(Conditional):
    def __init__(self, *cond, **kwcond):
        Conditional.__init__(self, getChild, *cond, **kwcond)
class Parent(Conditional):
    def __init__(self, *cond, **kwcond):
        Conditional.__init__(self, getParent, *cond, **kwcond)
class Sibling(Conditional):
    def __init__(self, *cond, **kwcond):
        Conditional.__init__(self, getSibling, *cond, **kwcond)
class Root(Conditional):
    def __init__(self, *cond, **kwcond):
        Conditional.__init__(self, getRoot, *cond, **kwcond)
class Ancestor(Conditional):
    def __init__(self, *cond, **kwcond):
        Conditional.__init__(self, getAncestor, *cond, **kwcond)
class Self(Pattern):
    def getNode(self, node): return node
class Serial(Pattern):
    def __init__(self, *conditionals):
        self.conditionals = conditionals
    def getNode(self, node):
        for c in self.conditionals:
            if not node: return
            node = c.getNode(node)
        return node
    


class FirstMatch(Pattern):
    def __init__(self, *rules):
        self.rules = rules
    def getNode(self, node):
        for rule in self.rules:
            n = rule.getNode(node)
            if n: return n

class Lowest(Pattern):
    def __init__(self, rel, pos):
        self.rel = rel
        self.pos = pos
    def getNode(self, node):
        lowest = node
        while getChild(lowest, self.rel, pos=self.pos):
            lowest = getChild(lowest, self.rel, pos=self.pos)
        return lowest

class Identifier(object):
    def __init__(self, db, debug=None):
        self.rules = []
        self.db = db
        self.debugfunc = debug
        self.lemma_set_dict = {}
    def debug(self, *args, **kargs):
        if not self.debugfunc: return
        s = "%s: %s" % (sys._getframe(2).f_code.co_name, ", ".join(map(str, args) + ["%s=%s" % kv for kv in kargs.iteritems()]))
        self.debugfunc(s)
    def findFrames(self, tree):
        return toolkit.filterTrue(map(self.getFrame, tree.getNodes()))
    def getFrame(self, node):
        for rule in self.rules:
            frame = rule.matches(node)
            if frame and frame.isComplete():
                return frame
    def hasLemma(self, node, lemmata, pos=None):
        if not node: return
        key = (pos, tuple(lemmata))
        lset = self.lemma_set_dict.get(key)
        if not lset:
            SQL = LEMMA_SQL % (",".join("'%s'" % w for w in lemmata))
            if pos: SQL += "and pos ='%s'" % pos
            lset = set(lid for (lid,) in self.db.doQuery(SQL))
            self.lemma_set_dict[key] = lset
        return node.word.lemma.id in lset

################### Specific rules ########################

class SPORule(DeclarativeRule):
    def __init__(self, identifier, postprocess=None, predicate=Self(), name="spo", **roles):
        roles['predicate'] = predicate
        DeclarativeRule.__init__(self, identifier, SPO, postprocess=postprocess, name=name, **roles)
    
    
class BronRule(DeclarativeRule):
    def __init__(self, identifier,  match=None, key=Self(), checks=None, postprocess=None, verbose=False, **roles):
        roles['key'] = key
        DeclarativeRule.__init__(self, identifier, Bron, postprocess=postprocess, verbose=verbose, **roles)
        self.match = match
        self.checks = checks
    def getFrame(self, node):
        self.debug(node.word.lemma, self.match)
        if self.match:
            pos, entries = self.match
            if pos and (node.word.lemma.pos <> pos): return
            for name, lemmata in entries.iteritems():
                if ((pos and self.identifier.hasLemma(node, lemmata, pos))
                    or ((not pos) and (node.word.lemma.label in lemmata))):
                    return self.frame(name)
        else:
            return super(BronRule, self).getFrame(node)

    def doCheck(self, frame):
        if self.checks:
            if type(self.checks) not in (tuple, list): self.checks = [self.checks]
            for check in self.checks:
                if not check.getNode(frame.key): return None
        return super(BronRule, self).doCheck(frame)

    

################# Frame Definitions ########

class Frame(Identity):
    def __init__(self, name, *args, **kargs):
        self.name = name
        for i, k in enumerate(self.__class__.ARGS):
            v = args[i] if i < len(args) else None
            self.__dict__[k] = v
        for k,v in kargs.items():
            self.__dict__[k] = v
                    
    def isComplete(self):
        return True
    def get(self, name):
        return self.__dict__.get(name)
    def has(self, *names):
        for name in names:
            if not self.get(name): return False
        return True
    def getConstituents(self):
        return tuple(sorted((k,v) for (k,v) in self.__dict__.items()
                            if isinstance(v, parsetree.ParseNode)))
    def getArgs(self):
        for argname in self.__class__.ARGS:
            arg = self.__dict__.get(argname)
            if not arg: break
            yield arg

    def identity(self):
        return self.__class__, self.name, self.getConstituents()
    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.name,
                               ", ".join("%s=%s" % kv for kv in self.getConstituents()))
    def __repr__(self):
        args = [arg.position for arg in self.getArgs()]
        kargs = {}
        for k,v in self.getConstituents():
            if v.position not in args:
                kargs[k] = v.position
        args = map(str, args)
        args += ["%s=%i" % (kv) for kv in kargs.items()]
        args = ",".join(args)
        return "%s(%s,%s)" % (self.__class__.__name__, `self.name`, args)
    def getNodesForConstituent(self, rol):
        constituents = self.getConstituents()
        stoplist = set([n for (r,n) in constituents])
        node = self.__getattribute__(rol)
        return set(node.getDescendants(stoplist=stoplist))

    def getNodesPerConstituent(self):
        for rol, node in self.getConstituents():
            yield rol, self.getNodesForConstituent(rol)
    
class Bron(Frame):
    ARGS = ["key","source","quote","addressee","negation"]
    def isComplete(self):
        return self.has('key', 'source', 'quote')

class Goal(Frame):
    ARGS = ["middel", "doel", "key"]
    def isComplete(self):
        return self.has("middel", "doel", "key")

class SPO(Frame):
    ARGS = ["subject","predicate","object","doelkey","doelobject"]
    def isComplete(self):
        #if self.has('doelkey') ^ self.has('doelobject'): return false # ^ = XOR
        if self.has('subject','predicate','object'): return True
        if self.has('subject', 'predicate'):
            self.name = 'SPO_su'
            return True
        if self.has('object', 'predicate'):
            self.name = 'SPO_obj'
            return True
        return False

################# Node Finding  #######################

def getTest(e):
    if not e: return lambda x: True
    if type(e) in (list, tuple, set): return e.__contains__
    return e.__eq__

def find(path, rel=None, word=None, lemma=None, pos=None, check=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    for n2, r in path:
        if word(n2.word.label) and lemma(n2.word.lemma.label) and pos(n2.word.lemma.pos) and rel(r.strip()):
            if (not check) or check(n2):
                return n2

def findLast(path, rel=None, word=None, lemma=None, pos=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    result = None
    for n2, r in path:
        if word(n2.word.label) and lemma(n2.word.lemma.label) and pos(n2.word.lemma.pos) and rel(r.strip()):
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
    return findLast(getAncestors(node), *cond, **kwcond) or node
    
def getDescendant(node, *cond, **kwcond):              
    return find(getDescendants(node), *cond, **kwcond)   

def getAncestors(node, stoplist=None):
    if not stoplist: stoplist = set()
    if not node: return
    if node in stoplist: return
    stoplist.add(node)
    for n2, rel in node.getParents():
        yield n2, rel
        for n3, rel in getAncestors(n2, stoplist):
            yield n3, rel

def getDescendants(node, stoplist = set()):
    if not node: return
    if node in stoplist: return
    stoplist.add(node)
    for n2, rel in node.getRelations():
        yield n2, rel
        for n3, rel in getDescendants(n2, stoplist):
            yield n3, rel

                
def getSibling(node, uprel, *downcond, **kwdowncond):
    return getChild(getParent(node, uprel), *downcond, **kwdowncond)

def isFrame(frame, name=None):
    if not frame: return False
    if not frame.isComplete(): return False
    if name is None: return True
    if type(name) in (str, unicode): return frame.name == name
    return frame.name in name

    
