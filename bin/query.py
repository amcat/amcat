#!/usr/bin/python

import dbtoolkit
import sys
import tableoutput

db = dbtoolkit.anokoDB()

outputs = ["plain", "csv"]
output = None
if sys.argv[1] in outputs:
    output = sys.argv[1]
    del sys.argv[1]

sql = " ".join(sys.argv[1:])


select = sql.strip().lower().startswith("select") or (sql.strip().lower() == "sp_who")
if select:
    sql = "SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED\n%s" % sql
    res, colnames = db.doQuery(sql, colnames=True, select=True)
    if output == "plain":
        tableoutput.printTable(res)
    elif output == "csv":
        tableoutput.table2csv(res)
    else:
        print tableoutput.table2unicode(res, colnames)
else:
    db.doQuery(sql)
    print "Executed successfully"
    
db.conn.commit()
