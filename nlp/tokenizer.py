#! /bin/env python2.3

import sys, re, string

def tokenize(str):
    #return re.sub("([\.!,;:'\-\(\)])"," \\1 " , str)
    res= re.sub("([^\w\s\-])"," \\1 " , str)
    res = re.sub("[\t ]+", " ", res).strip()
    if len(res) > 1 and res[1] not in string.uppercase:
        res = res[0].lower()+res[1:]
    return res


if __name__ == '__main__':
    for line in sys.stdin:
        line = tokenize( line )
        print line
