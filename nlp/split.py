"""
usage: split.py file1:0.5 file2:0.3 file3:0.2 < inputfile
"""

import random

def split(input, splitmap):

    files = []
    chances = []
    
    sum = 0
    for x,y in splitmap.items():
        sum += y
    
    chance = 0
    for x,y in splitmap.items():
        chance += y/sum
        chances.append(chance)
        files.append(open(x,'w'))

    for line in input:
        r = random.random()
        for f,c in zip(files, chances):
            if r <= c:
                f.write(line)
                break

if __name__ == '__main__':
    import sys
    input = sys.stdin
    splitmap = {}
    try:
        if len(sys.argv) == 1: raise Exception("Need arguments")
        for x in sys.argv[1:]:
            file, perc = x.split(":")
            splitmap[file] = float(perc)
    except:
        print __doc__

    split(input, splitmap)
    
