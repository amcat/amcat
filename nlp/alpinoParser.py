import os,re,urllib

cache = {}

def parse_remote(line):
    url = 'http://prauw:8000/%s'%urllib.quote(line)
    xml = urllib.urlopen(url).read()
    return xml

def parse(line, err=0):
    global cache
    if line in cache:
        print "FROM CACHE"
        if err:
            return cache[line], "<FROM CACHE>"
        else:
            return cache[line]
    
    #cout, cin, cerr =os.popen3('echo "%s" | /home/anoko/resources/AlpinoRt/Alpino.sh -flag treebank /tmp/x end_hook=xml -notk -parse' % line)
    f = open('/tmp/~toparse.txt', 'w')
    line = re.sub('\s+', ' ', line)
    f.write(line.strip())
    f.close()
    cmd = '/home/anoko/resources/AlpinoRt/Alpino.sh -flag treebank /tmp/x end_hook=xml -notk -parse < /tmp/~toparse.txt >/tmp/x/out 2>/tmp/x/err'
    os.system(cmd)

    #print cmd
    #print line
    #cout.close()

    e = open('/tmp/x/out').read() + open('/tmp/x/err').read()
    out = open("/tmp/x/1.xml").read()

    cache[line] = out
    if len(cache) > 50:
        cache = {}
    print "Added to cache, cache size now %s"%len(cache)

    if err:
        return out, e
    else:
        return out
    
if __name__=='__main__':
    import sys
    print parse_remote(sys.stdin.read())
