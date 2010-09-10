from __future__ import with_statement
import subprocess, time, threading, re, toolkit
from contextlib import contextmanager

RESOURCES = "/home/amcat/resources"

CMD = 'java -cp %s/jars/stanford-parser-2008-10-30.jar -mx200m edu.stanford.nlp.parser.lexparser.LexicalizedParser -sentences -retainTMPSubcategories -outputFormat "wordsAndTags,typedDependencies" -outputFormatOptions "stem,basicDependencies" %s/files/englishPCFG.ser.gz -' 

STANFORD_ANALYSISID=4
ENGLISH=1

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
    def __init__(self, resources=RESOURCES):
        cmd = CMD % (resources, resources)
        self.p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
        map(self.expectErr, ("Loading parser","Parsing file:"))

    def expectErr(self, msg):
        line = self.p.stderr.readline()
        if not line.startswith(msg):
            raise Exception("Unexpected parser message. Expecting: '%s*', got %r" % (msg, line))
        
    def parse(self, sent):
        sent = sent.strip()
        if sent and sent[-1] not in ".?;!": sent += "."
        self.p.stdin.write(sent)
        self.p.stdin.write("\n")

        words = self.p.stderr.readline()
        m = re.match(r"Parsing \[sent. \d+ len. \d+\]: \[(.*)\]", words)
        if not m: raise Exception("Cannot parse: %r" % words)
        words = m.group(1).split(", ")
        
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

        return words, pos, triples
    def stop(self):
        self.p.stdin.close()

def pos2token(position, w, s):
    lemma, pos = s.rsplit("/", 1)
    poscat = STANFORD_POS[pos]
    return (position, w, lemma, poscat, pos,'')
    
class StanfordParser(object):
    def __init__(self, *args, **kargs):
        self.parserArgs = args
        self.parserKargs = kargs
        self.restart()
    def parse(self, sentence):
        sentence = toolkit.clean(sentence, level=1)
        words, pos, triples = self.parser.parse(sentence)
        pos = pos[0].replace("\n","").split(" ")
        if len(pos) <> len(words):
            raise Exception("Words %r do not match pos %r" % (words, pos))
        tokens = [pos2token(i+1, w, s) for (i,(w,s)) in enumerate(zip(words, pos))]
        for triple in triples:
            m = re.match(r"([\w&]+)\((.+)-(\d+), (.+)-(\d+)\)", triple)
            if not m:
                #raise Exception("Cannot parse triple %r" % (triple))
                toolkit.warn("Cannot parse triple %r" % (triple))
                continue
            rel, t1, p1, t2, p2 = m.groups()
            tok1 = tokens[int(p1)-1]
            tok2 = tokens[int(p2)-1]
            yield tok1, rel, tok2
    def stop(self):
        if not getattr(self, 'parser', None): return 
        log = self.parser.stop()
        self.parser = None
        return log
    def restart(self):
        log = self.stop()
        self.parser = StanfordJavaParser(*self.parserArgs, **self.parserKargs)
        return log
    def __del__(self):
        self.stop()
        

@contextmanager
def stanfordParser(*args, **kargs):
    p = None
    try:
        p = StanfordParser(*args, **kargs)
        yield p
    finally:
        if p is not None:
            p.stop()

        
if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        toolkit.warn("Usage: stanford.py SID-or-SENTENCE")
        sys.exit()
    try:
        sid = int(sys.argv[1])
    except:
        sid = None

    if sid:
        import dbtoolkit, sentence
        db = dbtoolkit.amcatDB()
        s = sentence.Sentence(db, sid)
        sent = s.text
        print toolkit.clean(sent, level=1)
    else:
        sent = " ".join(sys.argv[1:])
    with stanfordParser() as p:
        print list(p.parse(sent))


    

        
    
