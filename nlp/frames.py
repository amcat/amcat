from __future__ import with_statement
from toolkit import Identity
import toolkit
import sys
from contextlib import contextmanager
import graph

############# INTERFACE ETC. ################

LEMMA_SQL = """select distinct l.lemmaid from words_lemmata l inner join words_words w on l.lemmaid = w.lemmaid inner join words_strings s on s.stringid = w.stringid where string in (%s)"""




class Rule(object):
    def __init__(self, identifier, verbose=False):
        self.identifier = identifier
        self.verbose = verbose
    def debug(self, *args, **kargs):
        if self.verbose: self.identifier.debug(*args, **kargs)
    def debugindent(self, *args, **kargs):
        return self.identifier.debugindent(*args, **kargs)
class DeclarativeRule(Rule):
    def __init__(self, identifier, frame, condition=None, postprocess=None, verbose=None, name=None, rulename=None, **roles):
        if verbose is None: verbose = not str(rulename).startswith("_")
        Rule.__init__(self, identifier, verbose)
        self.frame = frame
        self.condition = condition
        self.postprocess = postprocess
        self.roles = roles
        self.name = name
        self.rulename = rulename or "?"
    def getFrame(self, node):
        return self.frame(name=self.name, rulename=self.rulename)
    def matches(self, node):
        self.debug("  Applying rule %s"% self)
        frame = self.getFrame(node)
        if not frame: return
        for role, pattern in self.roles.iteritems():
            n = pattern.getNode(self, node)
            self.debug("  Found node %s for role %s" % (n, role))
            if n: frame.__dict__[role] = n
        frame = self.doPostProcess(frame)
        frame = self.doCheck(frame)
        return frame

    def doPostProcess(self, frame):
        self.debug("Postproces: %s "% frame)
        if self.postprocess: frame = self.postprocess(self.identifier, frame)
        self.debug("Postproces: ---> %s "% frame)
        return frame
      
    def doCheck(self, frame):
        if self.condition:
            self.debug("Condition: %s "% frame)
            conds = self.condition
            if callable(conds): conds = [conds]
            for cond in conds:
                if not cond(self, frame):
                    self.debug("Condition: FALSE ")
                    return None
        return frame
    def __str__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.frame.__name__, self.rulename) 
          
class FunctionRule(object):
    def __init__(self, db, function):
        Rule.__init__(self, db)
        self.function = function
    def matches(self, node):
        return self.function(node)

    
    
class Pattern(object):
    def __init__(self, func=None):
        self.func = func
    def getNode(self, rule, node):
        return self.func(node)
class Conditional(Pattern):
    def __init__(self, func, *cond, **kwcond):
        self.func = func
        self.cond = cond
        self.kwcond = kwcond
    def getNode(self, rule, node):
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
    def getNode(self, rule, node): return node
class Serial(Pattern):
    def __init__(self, *conditionals):
        self.conditionals = conditionals
    def getNode(self, rule, node):
        for c in self.conditionals:
            if not node: return
            node = c.getNode(rule, node)
        return node
    


class FirstMatch(Pattern):
    def __init__(self, *rules):
        self.rules = rules
    def getNode(self, rule, node):
        with rule.debugindent("FirstMatch") as d:
            for r in self.rules:
                n = r.getNode(rule, node)
                if n:
                    return n

class Lowest(Pattern):
    def __init__(self, rel, pos):
        self.rel = rel
        self.pos = pos
    def getNode(self, rule, node):
        lowest = node
        while getChild(lowest, self.rel, pos=self.pos):
            lowest = getChild(lowest, self.rel, pos=self.pos)
        return lowest

class Highest(Pattern):
    def __init__(self, rel, pos):
        self.rel = rel
        self.pos = pos
    def getNode(self, rule, node):
        highest = node
        while getParent(highest, self.rel, pos=self.pos):
            highest = getParent(highest, self.rel, pos=self.pos)
        return highest
    
class Identifier(object):
    def __init__(self, db, debug=None):
        self.rules = []
        self.db = db
        self.debugfunc = debug
        self.lemma_set_dict = {}
    def debug(self, msg=None, indent=None, adddepth=0):
        if not self.debugfunc: return
        func = sys._getframe(2+adddepth).f_code.co_name
        self.debugfunc(msg, func, indent)
        #self.debugfunc(func)
    @contextmanager
    def debugindent(self, msg):
        try:
            self.debug("Entering %s" % msg, indent=1, adddepth=1)
            yield None
        finally:
            self.debug("Leaving %s" % msg, indent=-1, adddepth=1) 
    def findFrames(self, tree):
        for node in tree.getNodes():
            f = self.getFrame(node)
            if f: yield f
    def getFrame(self, node):
        with self.debugindent("getFrame(%s)" % node):
            frames = set()
            for i, rule in enumerate(self.rules):
                frame = rule.matches(node)
                if frame and frame.isComplete():
                    self.debug("-->  Frame %s found in rule %s!"% (frame, rule))
                    frame.rulerank = i
                    frames.add(frame)
                if frame: self.debug("Found frame %s, not complete" % frame)
            if frames:
                frames = sorted(frames, key=framesort)
                self.debug("Rank ordered frames: %s" % frames)
                return frames[0]
    def hasLemma(self, node, lemmata, pos=None):
        if not node: return
        if "_" in str(node.word.lemma): # geef_aan etc, zie 34755418
            if pos and (pos<> node.word.lemma.pos): return False
            self.debug("_lemma %s in lemmata? %s (lemmata=%s)" % (node.word.lemma.label,node.word.lemma.label in lemmata, lemmata))
            return str(node.word.lemma) in lemmata
        key = (pos, tuple(lemmata))
        lset = self.lemma_set_dict.get(key)
        if not lset:
            SQL = LEMMA_SQL % (",".join("'%s'" % w for w in lemmata))
            if pos: SQL += "and pos ='%s'" % pos
            lset = set(lid for (lid,) in self.db.doQuery(SQL))
            self.debug(SQL)
            self.debug(lset)
            self.lemma_set_dict[key] = lset
        return node.word.lemma.id in lset

def framesort(frame):
    return (int(frame.isComplete()), frame.rulerank)
    
################### Specific rules ########################

class SPORule(DeclarativeRule):
    def __init__(self, identifier, rulename, postprocess=None, predicate=Self(), name="spo",  **roles):
        roles['predicate'] = predicate
        DeclarativeRule.__init__(self, identifier, SPO, postprocess=postprocess, name=name, rulename=rulename, **roles)
    
    
class BronRule(DeclarativeRule):
    def __init__(self, identifier, rulename,  match=None, key=Self(), checks=None, postprocess=None, verbose=None, **roles):
        roles['key'] = key
        DeclarativeRule.__init__(self, identifier, Bron, postprocess=postprocess, verbose=verbose, rulename=rulename, **roles)
        self.match = match
        self.checks = checks
    def getFrame(self, node):
        if self.match:
            pos, entries = self.match
            if pos and (node.word.lemma.pos.lower() <> pos.lower()): return
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
                if not check.getNode(self, frame.key): return None
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
                            if isinstance(v, graph.Node)))
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

class Cause(Frame):
    ARGS = ["dueTo", "consequence", "key"]
    def isComplete(self):
        return self.has("dueTo", "consequence", "key")

class NegCause(Frame):
    ARGS = ["despite", "consequence", "key"]
    def isComplete(self):
        return self.has("despite", "consequence", "key")

class Succession(Frame):
    ARGS = ["precedent", "consequence", "key"]
    def isComplete(self):
        return self.has("precedent", "consequence", "key")
        

class Assume(Frame):
    ARGS = ["assumption", "consequence", "key"]
    def isComplete(self):
        return self.has("assumption", "consequence", "key")


class SPO(Frame):
    ARGS = ["subject","predicate","object","doelkey","doelobject"]
    def isComplete(self):
        #if self.has('doelkey') ^ self.has('doelobject'): return false # ^ = XOR
        if self.has('subject','predicate','object'): return True
        if self.rulename == "passief": return
        if self.has('subject', 'predicate'):
            self.name = 'SPO_su'
            return 2
        if self.has('object', 'predicate'):
            self.name = 'SPO_obj'
            return 2
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
        if word(str(n2.word)) and lemma(str(n2.word.lemma)) and pos(n2.word.lemma.pos) and rel(str(r).strip()):
            if (not check) or check(n2):
                return n2

def findLast(path, rel=None, word=None, lemma=None, pos=None):
    if not path: return
    word, lemma, pos, rel = map(getTest, (word, lemma, pos, rel))
    result = None
    for n2, r in path:
        if word(str(n2.word)) and lemma(str(n2.word.lemma)) and pos(n2.word.lemma.pos) and rel(str(r).strip()):
            result = n2
        else:
            return result
    return result
        
def getChild(node, *cond, **kwcond):
    return find(node and node.children, *cond, **kwcond)

def getParent(node, *cond, **kwcond):
    return find(node and node.parents, *cond, **kwcond)
        
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
    for n2, rel in node.parents:
        yield n2, rel
        for n3, rel in getAncestors(n2, stoplist):
            yield n3, rel

def getDescendants(node, stoplist = set()):
    if not node: return
    if node in stoplist: return
    stoplist.add(node)
    for n2, rel in node.children:
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

    
