import toolkit

TABLES = ["projects", "batches", "articles", "texts"]
KEYS = {"articles" : {"batches"  : ("id", "batchid")},
        "batches"  : {"projects" : ("id", "projectid")},
        "texts"    : {"articles" : ("id", "articleid")}
        }

class Query:
    def __init__(this, fields, tables=["articles"], criteria=[], groupby=[], orderby=[]):
        this.fields = fields
        this.tables = tables
        this.criteria = criteria
        this.groupby = groupby
        this.orderby = orderby

    def orderbyClause(this):
        if this.orderby:
            return " ORDER BY %s " % ", ".join(this.orderby)
        else:
            return ""

    def groupbyClause(this):
        if this.groupby:
            return " GROUP BY %s " % ", ".join(this.groupby)
        else:
            return ""

    def whereClause(this):
        if this.criteria:
            if toolkit.isSequence(this.criteria):
                return " WHERE (%s) " % ") AND (".join(this.criteria)
            else:
                return this.criteria.where()
        else:
            return ""

    def fieldsClause(this):
        return ", ".join(this.fields)

    def fromClause(this):
        # order tables
        t = []
        for table in TABLES:
            if table in this.tables:
                t.append(table)

        if len(t) > 1:
            return " FROM %s " % reduce(lambda sql,table: connect_table(sql, table, t), t)
        else:
            return " FROM %s " % t[0]

    def sql(this):
        return "SELECT " + '\n'.join((this.fieldsClause(), this.fromClause(),
                                      this.whereClause(),this.groupbyClause(),this.orderbyClause()))

def connect_table(sql, table, tables):
    # find out table to connect to
    indent = "  " * (len(tables) - tables.index(table))
    for t in tables[0:tables.index(table)]:
       if t in KEYS[table]:
           keys = KEYS[table][t]
           return "\n%s(%s\n%s INNER JOIN %s \n%s ON %s.%s=%s.%s\n%s)" % (indent,sql, indent,table,indent, t, keys[0], table, keys[1], indent)


if __name__ == '__main__':
    q = Query(["name","headline","fulltext"], ["articles","projects","texts","batches"])
    print q.sql()
