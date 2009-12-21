#!/usr/bin/python

import dbtoolkit
import sys
import tableoutput

db = dbtoolkit.anokoDB()

sql = " ".join(sys.argv[1:])

select = sql.strip().lower().startswith("select")
if select:
    res, colnames = db.doQuery(sql, colnames=True)
    print tableoutput.table2ascii(res, colnames)
else:
    db.doQuery(sql)
    print "Executed successfully"
    
db.conn.commit()
