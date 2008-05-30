#! /bin/env python2.3

import cnlp

def tokenize(str):
    return cnlp.tokenize(str)

if __name__ == '__main__':
    import sys
    for line in sys.stdin:
        line = tokenize( line )
        sys.stdout.write(line)
