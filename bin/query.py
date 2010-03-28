#!/usr/bin/python

import dbtoolkit
import sys
import tableoutput

db = dbtoolkit.anokoDB()

outputs = ["plain"]
output = None
if sys.argv[1] in outputs:
    output = sys.argv[1]
    del sys.argv[1]

sql = " ".join(sys.argv[1:])

select = sql.strip().lower().startswith("select")
if select:
    res, colnames = db.doQuery(sql, colnames=True)
    if output == "plain":
        tableoutput.printTable(res)
    else:
        print tableoutput.table2unicode(res, colnames)
else:
    db.doQuery(sql)
    print "Executed successfully"
    
db.conn.commit()
