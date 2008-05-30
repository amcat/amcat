"""
countWords.py [OPTIONS] [WORDLIST]< IDLIST

Counts the words in the given articles and outputs a file containing
one 'word hits' pair per line. If WORDLIST is specified, count only
words from that list, and return in that order (ignores -s). The list
should contain one word per line, breaking at the first tab.

Options:
-s         sorts the word list in descending order
--help     display this information and exit
-w         require that each word starts with an alphabetical character
-l         lookup lemmatized articles, output lemma/pos, where the
           tag is the first character of the standard tag, except
           for articles and auxilliary verbs, which get R and H
"""

import sys, dbtoolkit, tokenize, toolkit, string

fixedList = None
if len(sys.argv)>1 and not sys.argv[-1].startswith('-'):
    toolkit.warn('Reading word list from %s' % sys.argv[-1], newline=0)
    fixedList = [line.strip().split("\t")[0] for line in open(sys.argv[-1]) if line.strip()]
    toolkit.warn('; %s words read' % len(fixedList))

sorted = '-s' in sys.argv
wordsonly = '-w' in sys.argv
lemmapos = '-l' in sys.argv
type= lemmapos and 4 or 2

if '--help' in sys.argv:
    print __doc__
    sys.exit(2)

counts = toolkit.DefaultDict(0)

def splitword(word):
    wlp = word.split("/")
    
    if len(wlp) < 3:
        POS = "?"
        lemma = wlp[0].strip()
        toolkit.warn("Cannot split '%s', taking lemma=word=%s, POS=?" % (word, lemma))
    else:
        POS = wlp[1]
        lemma = word.split("/")[2].strip()

    if POS[:6] == 'v(hulp': POS = 'Vh'
    elif POS[:3] == 'art' : POS = 'Art'
    else: POS = POS.split('(')[0]
    return lemma+"/"+POS

for article in dbtoolkit.Articles(tick=True,type=type):
    text = article.fulltext()
    if not lemmapos: text = tokenize.tokenize(text)
    text = toolkit.clean(text, level=1,lower=1)
    for word in text.split(" "):
        if not word: continue
        if wordsonly and not word[0] in string.ascii_lowercase: continue
        if lemmapos: word = splitword(word)
        counts[word] += 1

if fixedList:
    items = [[word, counts.get(word,0)] for word in fixedList]
elif sorted:
    toolkit.warn("Sorting...")
    items =toolkit.sortByValue(counts, reverse=1)
else:
    items = counts.items()
    
for word, count in items:
    print "%s\t%s" % (word, count)
