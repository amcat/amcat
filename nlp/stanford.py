import sys, subprocess, time, threading, lemmata, re, parsetree

CMD = 'java -cp /home/amcat/resources/jars/stanford-parser-2008-10-30.jar -mx200m edu.stanford.nlp.parser.lexparser.LexicalizedParser -sentences -retainTMPSubcategories -outputFormat "wordsAndTags,typedDependencies" -outputFormatOptions "stem" /home/amcat/resources/files/englishPCFG.ser.gz -'

STANFORD_POS = {
   '$' :'.',
   '"' :'.',
    "'" :'.',
   '``' : '.',
   "''" : '.',
   '(' :'.',
   ')' :'.',
   '-LRB-' : '.',
   '-RRB-' : '.',
   ',' :'.',
   '--' :'.',
   '.' :'.',
   ':' :'.',
   'CC' :'C',
   'CD' :'Q',
   'DT' :'D',
   'EX' :'R',
   'FW' :'?',
   'IN' :'P',
   'JJ' :'A',
   'JJR' :'A',
   'JJS' :'A',
   'LS' :'Q',
   'MD' :'V',
   'NN' :'N',
   'NNP' :'N',
   'NNPS' :'N',
   'NNS' :'N',
   'PDT' :'D',
   'POS' :'O',
   'PRP' :'O',
   'PRP$' :'O',
   'RB' :'B',
   'RBR' :'B',
   'RBS' :'B',
   'RP' :'R',
   'SYM' :'.',
   'TO' :'R',
   'UH' :'I',
   'VB' :'V',
   'VBD' :'V',
   'VBG' :'V',
   'VBN' :'V',
   'VBP' :'V',
   'VBZ' :'V',
   'WDT' :'D',
   'WP' :'O',
   'WP$' :'O',
   'WRB' :'B',
    }


class Reader(threading.Thread):
    def __init__(self, stream):
        threading.Thread.__init__(self)
        self.stream = stream
        self.out = ""
        self.stop = False
    def run(self):
        while not self.stop:
            self.out += self.stream.readline() + "\n"


class StanfordJavaParser(object):
    def __init__(self):
        self.p = subprocess.Popen(CMD, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        self.log = Reader(self.p.stderr)
        self.log.start()
    def parse(self, sent):
        self.p.stdin.write(sent)
        self.p.stdin.write("\n")
        pos = []
        while True:
            line = self.p.stdout.readline()
            if not line.strip(): break
            pos.append(line)
        triples = []
        while True:
            line = self.p.stdout.readline()
            if not line.strip(): break
            triples.append(line)    
        return pos, triples
    def stop(self):
        self.log.stop = True
        self.p.stdin.close()
        return self.log.out

def pos2token(position, s):
    word, pos = s.split("/")
    poscat = STANFORD_POS[pos]
    return lemmata.Token(position, word, word, poscat, pos,'')
    
    
class StanfordParser(object):
    def __init__(self):
        self.parser = StanfordJavaParser()
    def parse(self, sentence):
        pos, triples = self.parser.parse(sentence)
        pos = pos[0].replace("\n","")
        tokens = [pos2token(i+1, s) for (i,s) in enumerate(pos.split(" "))]
        for triple in triples:
            m = re.match(r"(\w+)\((.+)-(\d+), (.+)-(\d+)\)", triple)
            if not m:
                raise Exception(triple)
            rel, t1, p1, t2, p2 = m.groups()
            tok1 = tokens[int(p1)-1]
            tok2 = tokens[int(p2)-1]
            yield tok1, rel, tok2
    def stop(self):
        if not self.parser: return None
        log = self.parser.stop()
        self.parser = None
        return log
    def __del__(self):
        self.stop()
        
def parseOne(sent):
    s = StanfordParser()
    try:
        return s.parse(sent)
    finally:
        s.stop()
            
def parseTree(sent):
    s = StanfordParser()
    words = {}
    p = parsetree.ParseTree(None)
    for (parent, rel, child) in s.parse(sent):
        if parent not in words:
            words[parent] = parsetree.ParseNode(p, parent, parent.position)
        if child not in words:
            words[child] = parsetree.ParseNode(p, child, child.position) 
        p.addTriple(words[parent], words[child], rel)
    s.stop()
    return p
        
if __name__ == '__main__':
    import sys
    p = parseTree(" ".join(sys.argv[1:]))
    #p.printTree(output="/home/amcat/www-plain/test/test.png")
    import bronnen_en
    bronnen = list(bronnen_en.findBronnen(p))
    print bronnen


    

        
    
