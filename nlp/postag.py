import os, random,re, os.path

TEXT_TYPE=4

class Tagger:
    # For compatibility with mbtag
    def tagtext(self, txt):
        return tag(txt)

def tag(txt):
    txt = re.sub("\n ?\n(?: ?\n)*","\n\n@@@@\n\n",txt)
    o = None
    if not os.path.exists("/tmp/tag_articles"):
        os.mkdir("/tmp/tag_articles")
    while not o:
        try:
            rnd = int(random.random()*100000)
            fn = '/tmp/tag_articles/tmp_article_%s'%rnd
            o = open(fn, 'w')
        except IOError:
            pass
    o.write(txt + " ")
    o.close()
    res = os.popen2('tag %s 2>/dev/null' % fn)[1].read().strip()
    #print `res[:400]`
    res = re.sub(r"(?<=\n)@@@@/Misc\(symbool\) ?(?=\n|$)", "", res)
    return res

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        txt = " ".join(sys.argv[1:])
    else:
        txt = sys.stdin.readlines()
    print tag(txt)
