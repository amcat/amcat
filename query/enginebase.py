"""
Query Engine Base class and module
Does 'everything except for getList', ie everthing except for actually getting data
"""

import sys, table3, idlabel

def postprocess(table, sortfields, limit, offset):
    if sortfields:
        def comparator(x,y):
            for concept, asc in sortfields:
                if concept in table.concepts:
                    c = cmp(x[table.concepts.index(concept)],y[table.concepts.index(concept)])
                    if c: return c * (1 if asc else -1)
            return 0
        table.data.sort(comparator)

    if limit or offset:
        if not offset:
            offset = 0
        if limit:
            table.data = table.data[offset:offset+limit]
        else:
            table.data = table.data[offset:]

def makedistinct(rows):
    seen = set()
    for row in rows:
        if row in seen: continue
        yield row
        seen.add(row)

class QueryEngineBase(object):
    def __init__(self, datamodel, log=False, profile=False):
        self.log = log
        self.profile = profile and []
        self.model = datamodel

    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None, distinct=False):
        abstract

    def getTable(self, rows, columns, cellagr, filters=None):
        groupby = rows+columns
        select = groupby + [a.column for a in cellagr]

        table = self.getList(select, filters)

        aggTable = aggregate(table, groupby, cellagr)
        result = table3.DataTable()
        aggTable = list(aggTable)
                
        num_rows = len(rows)
        for k,v in aggTable:
            row = k[:num_rows]
            col = k[num_rows:]
            result.addValue(row, col, v)

        result.rows = sorted(result.rows)
        result.columns = sorted(result.columns)
                
        return result

    def getProfileTable(self):
        if self.profile is not None:
            return table3.ListTable(self.profile, ["Select", "Filter", "Sort", "Limit", "Offset", "Data", "Post"])
    def printProfile(self, stream=sys.stdout, htmlgenerator=False, useunicode=True, encoding="utf-8"):
        data = self.getProfileTable()
        if htmlgenerator:
            if htmlgenerator == True: htmlgenerator = tableoutput.HTMLGenerator()
            htmlgenerator.generate(data, stream)
        else:
            result = tableoutput.table2unicode(data, formats=["%s", "%s", "%s", "%s", "%s", "%4.2f", "%4.2f"], useunicode=useunicode)
            if type(result) == unicode: result = result.encode(encoding)
            print >>stream, result

    def getQuote(self, art, *args, **kargs):
        abstract
        
            
def aggregate(table, selectcolumns, aggregatecolumns):
    """
    table := table object
    selectcolumns := [columns over which to aggregate]
    aggregatecolumns := [AggregateColumnobjects containing the aggregatefunction]
    Returns a Generator with the tupled selected columns as key, and the aggregated values as the values
    """
    dict = {}
    ids2objs = {}
    def getid(o): return o.id if isinstance(o, idlabel.IDLabel) else o
    for row in table.getRows():
        objs = tuple(table.getValue(row, col) for col in selectcolumns)
        key = tuple(getid(o) for o in objs)
        if not dict.has_key(key):
            vals = tuple(a.getAggregateFunction() for a in aggregatecolumns)
            dict[key] = vals
            ids2objs[key] = objs
        for col, func in zip(aggregatecolumns, dict[key]):
            col.running(table, row, func)
    for key,funcs in dict.iteritems():
        values = tuple(col.final(func) for (col, func) in zip(aggregatecolumns, funcs))
        yield ids2objs[key], values

class ConceptTable(table3.Table):
    """Input: A list with concepts and data represented by a list"""
    def __init__(self, concepts,data):
        self.concepts = concepts
        self.data = data
    def getColumns(self):
        "returns the datasource.Concept object of the columns"
        return self.concepts
    def getRows(self):
        "returns the rows in data"
        return self.data
    def getValue(self, row, col):
        """
        Input: rowindex and columnindex
        Ouput: the value of the index
        """ 
        if type(col) <> int:
            try:
                col= self.concepts.index(col.column)
            except:
                col = self.concepts.index(col)
        return row[col]
    def getConcepts(self):
        """Returns the concept names of the table"""
        return self.concepts


