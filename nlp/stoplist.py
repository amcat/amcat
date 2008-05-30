import sys, toolkit, re

ONLY_WORD_CHARS = "-w" in sys.argv
if ONLY_WORD_CHARS: del(sys.argv[sys.argv.index("-w")])
NO_NUMBERS = "-n" in sys.argv
if NO_NUMBERS: del(sys.argv[sys.argv.index("-n")])

MIN_FREQ=0
if "-f" in sys.argv:
    MIN_FREQ = int(sys.argv[sys.argv.index("-f") + 1])
    del(sys.argv[sys.argv.index("-f") + 1])
    del(sys.argv[sys.argv.index("-f")])

if len(sys.argv) == 1:
    f = '/home/anoko/resources/files/stoplist_dutch.txt'
else:
    f = sys.argv[1]


stoplist = map(lambda x:x.strip(), open(f).readlines() )
stoplist = dict(zip(stoplist, [0]*len(stoplist)))

for line in sys.stdin:
    wrd = line.split('|')[0].strip()
    if wrd in stoplist: continue
    if ONLY_WORD_CHARS and re.search(r'\W',wrd): continue
    if NO_NUMBERS and re.search(r'\d',wrd): continue
    if MIN_FREQ:
        f =  int(line.split('|')[1].strip())
        if f < MIN_FREQ: continue
    print line,
    

