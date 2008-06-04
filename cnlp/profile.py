import toolkit, ccount
from timeit import Timer
import tokenizer

toolkit.ticker.warn("Reading words")
words = list(set(x.split("|")[0] for x in open('/home/anoko/resources/wvalemma/lemmadict_pos.txt')))
words = [w for w in words if ' ' not in w]

words = [(w, i) for (i,w) in enumerate(words)]
#words = (("de", 1),("het", 2),("kat", 3),("kater", 3),("blauwe", 5))

toolkit.ticker.warn("Initializing pcount")
worddict = dict(words)

toolkit.ticker.warn("Initializing ccount")
p = ccount.initialize(words)

toolkit.ticker.warn("Reading text...")
text = open('test.txt').read()
#text = "de blauwe kater ging met       de 'kat naar   Het\nHuis  "

def token():
    global text
    return tokenizer.tokenize(text)

def tokenc():
    global text
    return ccount.tokenize(text)

def count_c():
    global p, text
    return ccount.count(text, p, 1, 1)

def count_py():
    global worddict, text
    result = {}
    for word in text.lower().split():
        i = worddict.get(word, None)
        if i:
            if i in result:
                result[i] += 1
            else:
                result[i] = 1
    return result

def test(c,py):
    c = c()
    py = py()
    if c == py:
        print "OK!"
    else:
        print "FAILED!"
        for key in py:
            if py[key] <> c.get(key, None):
                print words[key], key, py[key], c.get(key, None)
        for key in c:
            if key not in py:
                print words[key], key, None, c[key]

toolkit.ticker.warn("Testing identical answers..")
text = token()
test(count_c, count_py)

toolkit.ticker.warn("Starting profiling...")

print "CCount:  %1.3f" % Timer('count_c()', 'from __main__ import count_c').timeit(1000)
print "Python:  %1.3f" % Timer('count_py()', 'from __main__ import count_py').timeit(1000)
print "Token :  %1.3f" % Timer('token()', 'from __main__ import token').timeit(1000)
print "CToken:  %1.3f" % Timer('tokenc()', 'from __main__ import tokenc').timeit(1000)
