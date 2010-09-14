#! /usr/bin/python

import dbtoolkit
db = dbtoolkit.amcatDB()


locks = {} # spid : lockedby
names = {} # spid : logi, host, db, cmd

def clean(x):
    if not x: return ""
    return x.strip()

for spid, ecid, status, loginame, hostname, blk, dbname, cmd in db.doQuery("sp_who", select=True):
    spid, blk = map(int, (spid, blk))
    if blk:
        locks[spid] = blk
    names[spid] = ("%3i" % spid, clean(loginame), clean(hostname), clean(dbname), clean(cmd))

if not locks:
    print "No locks!"
    import sys;sys.exit()

roots = sorted(set(s for s in locks.values() if s not in locks.keys()))


def prnt(spid, indent=0):
    print "%s- %s" % ("  "*indent, " / ".join(names[spid]))
    for k,v in locks.iteritems():
        if v == spid:
            prnt(k, indent+1)

for root in roots:
    prnt(root)

