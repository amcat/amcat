import sys,random
lines = sys.stdin.readlines()
random.shuffle(lines)
for l in lines:
    if l[-1] <> '\n':
        l += '\n'
    sys.stdout.write(l)
