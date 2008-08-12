#!/usr/bin/python

import dbtoolkit
import sys

db = dbtoolkit.anokoDB()

sql = " ".join(sys.argv[1:])

res = db.doQuery(sql)
if res:
    for row in res:
        print "\t".join("%s" % x for x in row)

db.conn.commit()
