"""Extract the html content of an Htm file using ChilKat library

NOTE: this is a temporary solution, hopefully the problem is also temporary!

Usage: python test3.py MHTFILE > HTMLFILE
"""

import chilkat, toolkit

def getHtml(mhtfile):
    mht = chilkat.CkMht()
    mht.UnlockComponent("Start my 30-day Trial")
    tempdir = "/tmp/mhttemp"
    fn = toolkit.tempfilename(suffix=".html", tempdir=tempdir)
    if mht.UnpackMHT(mhtfile,tempdir, fn,"files"):
        return open(fn).read()
    else:
        output = chilkat.CkString()
        mht.LastErrorText(output)
        raise Exception(output.getString())

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print >>sys.stderr, __doc__
        sys.exit()
    html = getHtml(sys.argv[1])
    print html
