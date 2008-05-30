import os, toolkit, os.path

def callpl(file, command, extra=None, deltemp =True):
    delfile = False
    if extra and not (extra.endswith(".pl") or extra.startswith("/")):
        if not os.path.exists("/tmp/prolog"):
            os.mkdir("/tmp/prolog")
        # assume extra is a string containing prolog rather than a file
        extra = toolkit.writefile(extra, tmpsuffix=".pl", tmpprefix="prolog/prolog-")
        delfile = deltemp
    
    cmd = 'prolog %s -s "%s" -t "%s"' % (extra and '-f "%s"' % extra, file, command)
    #toolkit.warn(cmd)
    out, err = toolkit.execute(cmd)
    err = cmd+"\n\n" + err
    if delfile:
        os.remove(extra)
    return out, err

def callplrec(file, command, extra=None, returnout=False, deltemp=True):
    out, err = callpl(file, command, extra, deltemp)

    result = []
    for line in out.split("\n"):
        if line.strip() == "---" and result and result[-1]:
            result.append({})
        kv = line.split(":")
        if len(kv) == 2:
            if not result: result.append({})
            result[-1][kv[0].strip()] = [int(x) for x in kv[1].strip().split(" ")]
    if result and not result[-1]: del(result[-1])

    if returnout:
        return result, (out, err)
    else:
        return result

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3:
        dummy, file, command = sys.argv
        extra = None
    elif len(sys.argv) == 4:
        dummy, file, command, extra = sys.argv
    else:
        print "Usage: python prolog.py FILE COMMAND [EXTRA]\nif EXTRA is '-', read prolog from stdin"
        sys.exit(1)

    if extra == "-":
        extra = sys.stdin.read()
        
    records, (out, err) = callplrec(file, command, extra, True)

    print "Raw output:\n%s\nRaw err:\n%s\n------\n" % (out, err)
    for record in records:
        print
        for k, v in record.items():
            print "%s : %s" % (k, v)
