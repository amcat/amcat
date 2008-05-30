import os, re, toolkit, prolog, alpino, Levenshtein

class Segment:
    def __init__(self, nodeids, text):
        self.nodeid = [int(nodeid) for nodeid in nodeids.split() if nodeid.strip()]
        self.text = str(text).strip()
    def __str__(self):
        return "%s" % self.text

class Bronconstructie:
    def __init__(self, record, parse, what):
        def get(key):
            ids = record.get(key, [])
            return [parse.findnode(id) for id in ids]
        self.key = get('key')
        self.subject = get('subject')
        self.object = get('object')
        self.ref = None
        self.status = None
        self.type = what
    def __str__(self):
        return "{K:%s S:%s O:%s}" % (alpino.wordids(self.key), alpino.text(self.subject), alpino.text(self.object))


def fromsid(sid, db):
    parse = alpino.getParse(sid, db)
    return fromparse(parse, db)

def fromparse(parse, db):
    srcs0, parse = surfacematch(parse, db)
    
    prologstr = parse.prolog()
    srcs, err1 = readpl(parse, True, 'source')
    srcs += srcs0
    spos, err2 = readpl(parse, True, 'spo')
    err = (err1[0] + "\n---==---\n"+ err2[0],
           err1[1] + "\n---==---\n"+ err2[1])

    for b in list(spos):
        for b2 in srcs:
            if overlap(b2.key, b.key):
                spos.remove(b)
                break

    return srcs, spos, err, parse

def surfacematch(parse, db):
    m = re.match("(.{,30}) : (.*)", parse.sentence)
    if m:
        src1 = m.group(1)
        quot1 = m.group(2)
        sent = "%s . %s" % (src1, quot1)
        parse = alpino.getParse(sent, db)
        key = parse.findnodebywordid('du')
        #print key.children
        if key and len(key.children) == 2:
            a = key.children[0]
            b = key.children[1]
            ad = Levenshtein.distance(unicode(alpino.text([a])), src1)
            bd = Levenshtein.distance(unicode(alpino.text([b])), src1)
            src,quot = (ad>bd) and (b,a) or (a,b)
            return [Bronconstructie({'key' : [key.id], 'subject': [src.id], 'object' : [quot.id]}, parse, 'source')], parse
    m = re.match("(.*) : ['\"](.*)['\"]?", parse.sentence)
    if m:
        src1 = m.group(1)
        quot1 = m.group(2)
        sent = "%s . %s" % (src1, quot1)
        #print sent
        parse = alpino.getParse(sent, db)
        key = parse.findnodebywordid('du')
        #print key.children
        if len(key.children) == 2:
            a = key.children[0]
            b = key.children[1]
            ad = Levenshtein.distance(unicode(alpino.text([a])), src1)
            bd = Levenshtein.distance(unicode(alpino.text([b])), src1)
            src,quot = (a>b) and (b,a) or (a,b)

            #print src.pos
            if src.cat == "smain":
                for n in src.children:
                    #print n.rel
                    if n.rel == "su":
                        src = n
                        break
            
            return [Bronconstructie({'key' : [key.id], 'subject': [src.id], 'object' : [quot.id]}, parse, 'source')], parse
    return [], parse

whats = {'source' : ('bronnen.pl', 'bronnen'), 'spo' : ('spo3.pl', 'spos')} 
    
def readpl(parse, returnoutput=False, what=None, prog="bronnen2.pl", call="bronnen2", path="/home/wva/projects/bronnen/"):
    if what:
        prog = whats[what][0]
        call = whats[what][1]
    prologstr = parse.prolog()
    call = "%s(z1)" % call
    recs, outerr = prolog.callplrec("%s%s" % (path, prog), call, prologstr, True)
    result = [Bronconstructie(rec, parse, what) for rec in recs]

    if returnoutput:
        return result, outerr
    else:
        return result

def overlap(ids, nodes):
    seta = set(i.indexed().id for i in ids)
    setb = set(node.indexed().id for node in nodes)
    #print seta, "=?=", setb, " -> ", " ".join(i.wordid for i in ids), "=?=", " ".join(i.wordid for i in nodes)
    return bool(seta & setb)

def containsAllNodes(nodesa, nodesb):
    idsb = set(i.indexed().id for i in nodesb)
    for a in nodesa:
        if not (a.optional or a.indexed().id in idsb): return False
    return True
        
def identical(nodesa, nodesb):
    return containsAllNodes(nodesa, nodesb) and containsAllNodes(nodesb, nodesa)

if __name__ =='__main__':
    import sys, dbtoolkit
    for b in fromsid(int(sys.argv[1]), dbtoolkit.anokoDB()):
        print b
        
    
