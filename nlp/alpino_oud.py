import re,sys,toolkit, os, tokenize, shutil
import xml.sax.handler, xml.sax, dot
from ctokenizer import tokenize

class Sentence:
    def __init__(self, xml):
        self.top = None
        self.sid = None
        self.sentencenr = None
        self.aid = None
        self.sentence = None
        self.xml = xml
        self.wordids = False
        
    def printh(self):
        output = '%s.%s "%s"\n'% (self.aid, self.sentencenr, self.sentence)
        return output + self.top.printh()

    def prologi(self, zinid):
        prolog = {"rel":[], "root":[], "pos":[], "be" :[], "wbe" : [], "id" : [], "cat" : []}
        self.top.prolog(zinid, prolog, set(), {})
        rels = []

        # remove duplicates
        for rel in ("rel","root","pos","be","wbe", "id", "cat"):
            prolog[rel] = list(set(prolog[rel]))

        # remove 'body' cycles
        edges = set() #set((zin, su, obj), ..) 
        for rel in prolog["rel"]:
            m = re.match("rel\((.*)\).", rel)
            z,s,r,o = m.group(1).split(",")
            if r.strip() == "body":
                rels.append(rel)
                edges.add((z,s,o))
#        print edges
        for rel in prolog["rel"]:
            m = re.match("rel\((.*)\).", rel)
            z,s,r,o = m.group(1).split(",")
            if r.strip() <> "body":
                #if (z,o,s) not in edges:
#                    print "%s %s %s %s" % (rel, z,s, o)
                    rels.append(rel)
    
                                        

        prolog["rel"] = rels
            
        self.wordids = True
        return prolog        

    def prolog(self, zinid="z1"):
        prolog = self.prologi(zinid)
        output = ("text(%s, '%s').\nsid(%s, %s).\n\n"
                  % (zinid, self.sentence.replace("'",'"'), zinid, self.sid))
        output += "\n\n".join("\n".join(prolog[x]) for x in ("rel","root","pos","be","wbe", "id", "cat"))
        return output

    def dot2(self):
        dot = 'digraph G {\ngraph [rankdir="BT"];\n'
        p = self.prologi("z1")

        for rel in p["rel"]:
            cmd, args = prologrel(rel)
            zinid, su, pre, obj = args
            sun = nodehead(self.findnodebywordid(su))
            objn = nodehead(self.findnodebywordid(obj))
            dot += '"%s" -> "%s" [label="%s"];\n' % (sun.word,  objn.word, pre)
        dot += '}\n'
        return dot
        
    def dot(self, nodedefs = {}):

        dot = ""
        nodes = set()
        for line in self.prologi("z1")["rel"]:
            cmd, args = prologrel(line)
            if cmd == "rel":
                zinid, su, pre, obj = args
                dot += '%s -> %s [label="%s"];\n' % (su,  obj, pre)
                nodes |= set((su, obj))
        for node in nodes:
            if node in nodedefs:
                dot = "%s [%s];\n" % (node, nodedefs[node]) + dot
        dot = 'digraph G {\ngraph [rankdir="BT",ranksep="0"];edge[dir="xnone",fontsize="10",fontcolor="1,0,.4",fontname="arial"];node[fontname="arial",fontsize="9",height=".2",shape="box",color="1,0,1"];\n%s\n}\n' % dot
        return dot 

    def dotImg(self, nodedefs = {}, **kargs):
        dtstr = self.dot(nodedefs)
        return dot.dot2img(dtstr,**kargs)

    def findnode(self, id, node=None):
        if not node: node = self.top
        if node.id == id: return node
        for n2 in node.children:
            r = self.findnode(id, n2)
            if r: return r
        return None

    def findnodebywordid(self, wordid, node=None):
        if not self.wordids: self.prologi("z1")
        if not node: node = self.top
        if node.wordid == wordid: return node
        for n2 in node.children:
            r = self.findnodebywordid(wordid, n2)
            if r: return r
        return None

    def findIndex(self, index):
        nodes = set()
        def recurse(node):
            if node.index == index: nodes.add(node)
            for child in node.children:
                recurse(child)
        recurse(self.top)
        for node in nodes:
            if node.children or node.word or node.root:
                return node
        return None
    
    def findAllCoIndexed(self, node):
        nodes = set((node,))
        def recurse(n2):
            if n2.index == node.index: nodes.add(n2)
            for child in n2.children:
                recurse(child)
        if node.index is not None: recurse(self.top)
        return nodes


def prologrel(line):
    m = re.match(r"(\w+)\(([^)]+)\)", line)
    if not m: raise Exception("Cannot parse %r" % line.strip())
    cmd = str(m.group(1).strip())
    args = [str(x.strip()) for x in m.group(2).split(",")]
    return cmd, args                        

class Node:
    def __init__(self, sentence = None, parent = None, begin = None, end = None, id = None, pos = None, rel = None, root = None, word = None, cat = None, index = None, **kargs):
        self.sentence = sentence
        self.parent = parent
        self.children = []
        self.begin = begin
        self.end = end
        self.id = id
        self.pos = pos
        self.rel = rel
        self.root = root
        self.word = word and str(word)
        self.cat = cat
        self.index = index
        self.wordid = None
        self.optional = False
        self.postag = None
        self.anaphora = None

    def addchild(self, node):
        self.children.append(node)

    def printh(self, indent = ""):
        output = "%s[%s %s]\n"%(indent, self.rel, self.word)
        for child in self.children:
            output += child.printh(indent + "  ")
        return output

    def indexed(self):
        if self.index and not (self.children or self.word or self.root):
            return self.sentence.findIndex(self.index)
        return self

    def getWordid(self):
        if not self.sentence.wordids: self.sentence.prologi("z1")
        return self.wordid

    def getPostag(self, db):
        if not self.postag:
            #print self.wordid, self.begin, self.end
            self.postag = postagdb(db, self.sentence.sid, self.begin, self.end)
        return self.postag
    
    def prolog(self, zinid, prolog, roots, indices):
        if self.rel in ("hd","rhd","crd","cmp"): return ""
        children = self.children
        n = self
        if not n.root:
            for child in self.children:
                if child.rel in ("hd","rhd","crd","cmp"):
                    n = child
        root = n.root

        if not root:
            if n.cat == 'mwu':
                rts = [c.root for c in n.children]
                root = "_".join([str(x) for x in rts])
                children = []

        if root:
            root = clean(root)
            self.wordid = root
            i = 1
            while self.wordid in roots:
                self.wordid = "%s%s" % (root, i)
                i += 1
            roots.add(self.wordid)
            
        index = self.index or n.index
        if index:
            if self.wordid:
                indices[index] = self.wordid
            else:
                self.wordid = indices.get(index, None)
        elif not self.wordid:
            c = self.cat
            if not c: c = self.rel
            if not c: c = "unknown"
            self.wordid = c
            i = 1
            while self.wordid in roots:
                self.wordid = "%s%s" % (c, i)
                i += 1
            roots.add(self.wordid)



        if not self.wordid:
            self.wordid = "token%i" % self.id

        if self.parent and self.parent.wordid:
            #if self.rel <> "body":
            prolog["rel"] += ["rel(%s, %s, %s, %s)." % (zinid, self.wordid, self.rel, self.parent.wordid)]
            
        if self.wordid:
            prolog["root"] += ["root(%s, %s, '%s')." % (zinid, self.wordid, root)]
            prolog["id"] += ["id(%s, %s, %i)." % (zinid, self.wordid, self.id)]
            pos = n.pos or "none"
            prolog["pos"] += ["pos(%s, %s, %s)." % (zinid, self.wordid, pos)]
            cat = n.cat or "none"
            prolog["cat"] += ["cat(%s, %s, %s)." % (zinid, self.wordid, cat)]
        if self.begin is not None and self.end is not None:
            prolog["be"] += ["beginend(%s, %s, %s, %s)." % (zinid, self.wordid, self.begin, self.end)]
        if n.begin is  not None and n.end is not None:
            prolog["wbe"] += ["wbeginend(%s, %s, %s, %s)." % (zinid, self.wordid, n.begin, n.end)]

        idd = False
        for p in prolog["id"]:
            if p.startswith("id(%s, %s" % (zinid, self.wordid)):
                idd = True
                break
        if not idd:
            prolog["id"] += ["id(%s, %s, %i)." % (zinid, self.wordid, self.id)]

        idd = False
        if self.parent and self.parent.wordid:
            for p in prolog["id"]:
                if p.startswith("id(%s, %s" % (zinid, self.parent.wordid)):
                    idd = True
                    break
            if not idd:
                prolog["id"] += ["id(%s, %s, %i)." % (zinid, self.parent.wordid, self.parent.id)]
        
        for child in children:
            child.prolog(zinid, prolog, roots, indices)


    def text(self):
        node = self.indexed()

        words = node.words()
        words.sort(lambda a,b: a[0] - b[0])
        return " ".join(str(word[1]) for word in words)

    def words(self):
        result = []
        if self.word: result += [(self.begin, self.word)]
        for child in self.children:
            result += child.words()
        return result
        
def text(nodes):
    return "; ".join(node.text() for node in nodes)

def wordids(nodes):
    return " ".join(node.getWordid() for node in nodes)

def words(nodes):
    return " ".join(node.word or node.getWordid() for node in nodes)

def nodes(nodelist):
    result = set()
    for node in nodelist:
        result |= children(node, result)
    return result

def children(node, blacklist = None):
    result = set((node,))
    if not blacklist: blacklist = set()
    if node not in blacklist:
        blacklist.add(node)
        if node.children:
            for child in node.children:
                result |= children(child, blacklist)
        result |= children(node.indexed(), blacklist)
    return result

def clean(word):
    #if toolkit.isNumeric(word): word = "num"
    if toolkit.isNumeric(word): word = "n_%s" % word
    if word[0] in "0123456789": word = "n_%s" % word
                                                
    word = re.sub(r"[\.,\(\)\'\"]","punc",word)
    word = re.sub(r"\W","x",word)
    word = word.lower()
    return word


maps = {u"\xef" : u"i", u"\xeb" : u"e", u"\xe9" : u"z"}

def val(x):
    if re.match(r"\d+$",x): return int(x)
    if re.match(r"(\d\.)+$",x): return float(x)
    x = toolkit.stripAccents(x)
    #for k,v in maps.items():
    #    x = x.replace(k, v)
    try:
        return str(x)
    except Exception, e:
        print >>sys.stderr, e
        print >>sys.stderr, `x`

textNames = ['sentence', 'sentencenr', 'articleid'] # Nodes waar tekst van moet worden opgeslagen

 
class AlpinoHandler(xml.sax.handler.ContentHandler):
    def __init__(self, xml):
        self.inText = False
        self.output = [] # array waar de prolog code in bewaard wordt
        self.xml = xml

    def startElement(self, name, attributes):
        if name == "alpino_ds":
            self.currentSent = Sentence(self.xml)
            self.stack = [None]
            self.output.append(self.currentSent)
        if name == "node":
            parent = self.stack[-1]
            attr = {'parent':parent}
            for k in attributes.keys():
                attr[str(k)] = val(attributes[k])
            node = Node(self.currentSent, **attr)
            self.stack.append(node)
            if parent: parent.addchild(node)
            else: self.currentSent.top = node
        if name in textNames:
            self.inText = True
            self.buffer = ""

    def characters(self, data):
        if self.inText:
            self.buffer += data
            

    def endElement(self, name):
        if name == "node":
            del(self.stack[-1])

        if name == "sentence": self.currentSent.sentence = self.buffer
        if name == "sentencenr": self.currentSent.sentencenr = int(self.buffer)
        if name == "articleid": self.currentSent.aid = int(self.buffer)


def fromString(xmlstr, sid):
    handler = AlpinoHandler(xmlstr)
    xml.sax.parseString(xmlstr, handler)
    parse = handler.output[0]
    parse.sid = sid
    return parse

TMP = '/tmp/treebank'
ALPINO = '/home/wva/toolkits/Alpino'

def getParseXML(sid_or_sentence, db=None):
    """
    Get the parse xml for the sid or sentence provided. If
    sid_or_sentence is a number, try to obtain the parse from the
    database. If it is a sentence, or if the parse is not found in
    the database, call Alpino to get the parse. If sid_or_sentence is
    a sentence, the db parameter may be omitted.  Guaranteed to
     return a parse xml string or throw an exception
    """
    parse, err, fn = None, None, None
    sid = toolkit.asInt(sid_or_sentence)
    sent = sid_or_sentence
    if not sid:
        sid = db.getValue("select sentenceid from sentences where articleid=35416866 and sentence=%s" % toolkit.quotesql(sent)) 
    if sid:
        # lookup parse by sentence id
        sent = db.getValue("select sentence from sentences where sentenceid=%i"%sid)
        parse = db.getValue("select parse from sentences_parses where sentenceid=%i"%sid)
        # check parse tokenization: old tokenizer tokenized pvda-er as pvda - er, which messes up the parse
        m = parse and re.search("<sentence>([^<]+)</sentence", parse)
        if m:
            ps = m.group(1).strip().replace("&apos;", "'").replace("&quot;", '"').replace("&amp;", "&").strip()
            sent = re.sub(r"(\w+)' ?(ers?)\b", r"\1-\2", sent)
            sent = re.sub(r"(\w+) - (\w+)", r"\1 . \2", sent)
            s2 = tokenize(sent).strip()
            #print s2
            clean = lambda x: re.sub(r"\s+"," ", x).lower().strip() 
            if clean(ps) <> clean(s2):
                #toolkit.warn("[alpino.py] %r <> %r, reparsing!" % (clean(ps), clean(s2)))
                db.doQuery("delete from sentences_parses where sentenceid=%i"%sid)
                parse = None
            
    if not parse:
        parse, err = parseone(sent, True)
        if not sid:
            sentnr = db.getValue("select max(sentnr) from sentences where articleid=35416866")
            sentnr = sentnr and sentnr + 1 or 1
            sid = db.insert("sentences", {'articleid': 35416866, 'parnr' : 1, 'sentnr' : sentnr,
                                          'sentence' : sent})
        db.insert("sentences_parses", {'sentenceid' : sid, 'parsejobid': 0, 'started' : 1, 'parse' : parse})
    if not parse:
        raise Exception("Could not parse sentence:\nsid: %s, sent: '%s', err: %s" % (sid, sent, err))

    return parse, sent, sid     

def getParse(sid_or_sentence, db):
    """
    Get the parse alpino.Sentence object for the sid or sentence
    provided. See getParseXML for more info.
    """
    parse, sent, sid = getParseXML(sid_or_sentence, db)
    parse = fromString(parse, sid)
    return parse    

def parseone(sentence, returnerr=False):
    nr = 1
    d = ((nr, sentence),)
    res = parse(d, returnerr)
    
    if len(res):
        return res[0][nr], res[1]
    else:
        return res[nr]

def parse(sentences, returnerrdir=False):
    tmp = toolkit.tempfilename(prefix="parse-")
    inp = "\n".join("%s|%s\n" % (sid, tokenize(s)) for (sid, s) in sentences)
    CMD = "ALPINO_HOME=%s %s/bin/Alpino -fast -flag treebank %s end_hook=xml -parse" % (ALPINO, ALPINO, tmp)

    toolkit.warn("[alpino.py] Parsing %r (%i sentences)" % (sentences[0][1][:30], len(sentences)))

    os.mkdir(tmp)
    out, err = toolkit.execute(CMD, inp)
    err = out + "\n" + err
    
    result = {}
    for sid, s in sentences:
        sid = int(sid)
        parse = None
        try:
            parse = open('%s/%i.xml' % (tmp, sid)).read()
        except Exception, e:
            print >>sys.stderr, e
            continue
        result[sid] = parse

    shutil.rmtree(tmp)

    if returnerrdir:
        return result, err
    else:
        return result

def postagdb(db, sid, start, end):
    sql = "select pos from sentences_postags where sentenceid=%i and start=%i and [end]=%i" % (sid, start, end)
    tag = db.getValue(sql)
    
    if tag: return tag

    if db.getValue("select sentenceid from sentences_postags where sentenceid=%i" % (sid)):
        return None

    result = None
    tags = postagsid(db, sid)
    for sid2, s2, e2, word, pos in tags:
        if s2 == start and e2 == end:
            result = pos
        db.insert("sentences_postags", {'sentenceid' : sid, 'start' : s2, '[end]' : e2, 'word':word, 'pos':pos}, retrieveIdent=0)
    return result

def postagsid(db, sid):
    sentence = db.getValue("select sentence from sentences where sentenceid=%i" % sid)
    return postag(((sid, sentence),))

def postag(sentences):
    inp = "\n".join("%s|%s\n" % (sid, tokenize(s)) for (sid, s) in sentences)
    CMD = "ALPINO_HOME=%s %s/bin/Alpino -fast end_hook=frames -parse" % (ALPINO, ALPINO)

    toolkit.warn("[alpino.py] Postagging %r (%i sentences)" % (sentences[0][1][:30], len(sentences)))


    out, err = toolkit.execute(CMD, inp)
    if err:
        toolkit.warn(err)
        #for line in err.split("\n"):
            #if line.strip() and not line.lower().startswith("warning"):
            #    raise Exception(err)
    
    result = []
    for line in out.split("\n"):
        expr = r"\|".join([r"([\w,|()\[\]{}'\"/]+)"] * 10)
                          
        m = re.match(expr, line)
        if m:
            word, pos, sid, start, end = m.groups()[:5]
            result.append((int(sid),int(start), int(end), word, pos))
        #else:
        #    print `line`
    return result

              
if __name__ == '__main__':

    print postag([(1, " ".join(sys.argv[1:]))])
    asdf
    import sys, dbtoolkit
    sid = int(sys.argv[1])
    start = int(sys.argv[2])
    end = start + 1
    print postagdb(dbtoolkit.anokoDB(), sid, start, end)
