"""
Query Engine
"""

import operation, mst, tabulatorstate
import os, time, sys
import toolkit
import table3, tableoutput

import filter, aggregator # not used, import to allow indirect access

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


class QueryEngine(object):
    def __init__(self, datamodel, log=False, profile=False):
        self.log = log
        self.profile = profile and []
        self.model = datamodel
        self.operationsFactory = operation.OperationsFactory()

    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None):
        T0 = time.time()
        route = getRoute(self.model, concepts, filters)
        state = tabulatorstate.State(None, route, filters)
        toolkit.ticker.warn("Starting reduction")
        while state.solution is None:
            best = toolkit.choose(self.operationsFactory.getOperations(state),
                                  lambda op: op.getUtility(state))
            #toolkit.ticker.warn("Reducing...")
            state = best.apply(state)
            #toolkit.ticker.warn("Cleaning...")
            clean(state, concepts)
        toolkit.ticker.warn("Done")
        solution = getColumns(state.solution, concepts)
        T1 = time.time()
        t = ConceptTable(concepts,solution)
        postprocess(t, sortfields, limit, offset)

        if type(self.profile) == list:
            T9 = time.time()
            self.profile.append([tostr(concepts), tostr(filters), tostr(sortfields, sort=True), limit, offset, T1-T0, T9-T1])
        return t

    def getTable(self, rows, columns, cellagr, filters=None):
        groupby = rows+columns
        select = groupby + [a.column for a in cellagr]

        table = self.getList(select, filters)

        aggTable = aggregate(table, groupby, cellagr)
        result = table3.DataTable()
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
            
def tostr(seq, sort=False):
    if seq:
        if sort:
            print `seq`
            return ", ".join("%s (%s)" % (f, a and "v" or "^") for (f,a) in seq)
        return ", ".join(map(str, seq))
            
def aggregate(table, selectcolumns, aggregatecolumns):
    """
    table := table object
    selectcolumns := [columns over which to aggregate]
    aggregatecolumns := [AggregateColumnobjects containing the aggregatefunction]
    Returns a Generator with the tupled selected columns as key, and the aggregated values as the values
    """
    dict = {}
    for row in table.getRows():
        key = tuple(table.getValue(row, col) for col in selectcolumns)
        if not dict.has_key(key):
            vals = tuple(a.getAggregateFunction() for a in aggregatecolumns)
            dict[key] = vals
        for col, func in zip(aggregatecolumns, dict[key]):
            col.running(table, row, func)
    for key,funcs in dict.iteritems():
        values = tuple(col.final(func) for (col, func) in zip(aggregatecolumns, funcs))
        yield key, values

def getRoute(model, concepts, filters):
    concepts = set(concepts) | set(f.concept for f in filters)
    return mst.getSolution(model.getMappings(), concepts)

def clean(state, goal):
    # we keep columns that (1) are in goal or (2) are contained in mappings
    for node in state.getNodes():
        if not node.data: continue
        keep = set(goal)
        for edge in state.edges:
            if edge.a == node:
                keep.add(edge.mapping.a)
            if edge.b == node:
                keep.add(edge.mapping.b)
        dellist = [i for (i, field) in enumerate(node.fields) if field not in keep]
        if not dellist: continue
        dellist.sort(reverse=True)
        for row in node.data:
            for i in dellist:
                del row[i]
        for i in dellist:
            del node.fields[i]

def getColumns(node, goal):
    if not node.data or node.fields == goal: return node.data
    indices = map(node.fields.index, goal)
    result = []
    for row in node.data:
        result.append(tuple(map(lambda i: row[i], indices)))
    return result

def getPossibleValues(db=None,field=None,customer=None, storedresult=759): 
    """
    Stoffer en blik vereist.

    db := dbtoolkit.amcatDB
    field := A known concept to the sourceinterface (one of the items on top of the file), with fixed values.

    Returns a list of possible values of the given field
    """

    import draftdatamodel
    datamodel = draftdatamodel.getDatamodel(db)
    if field == "merk":
        for datasource in datamodel._datasources:
            if isinstance(datasource,draftdatamodel.merkdatasource.MerkDataSource):
                if customer:
                    return datasource.customerbrands[customer]
                return datasource.brands
        return "Customers not found"

    if field == "customer":
        for datasource in datamodel._datasources:
            if isinstance(datasource,draftdatamodel.merkdatasource.MerkDataSource):
                return datasource.customers
        return "Customers not known"

    if field == "source":
        qry = """
        SELECT DISTINCT media.mediumid, media.name
        FROM            media
        INNER JOIN      articles
            ON          (articles.mediumid = media.mediumid)
        INNER JOIN      storedresults_articles
            ON          (storedresults_articles.articleid = articles.articleid)
        WHERE           storedresults_articles.storedresultid = %d
        ORDER BY        media.name ASC
        """ % (storedresult,)
        return db.doQuery(qry)

    if field == "sourcetype":
        qry = """
        SELECT DISTINCT media.sourcetypeid, media.type
        FROM            media
        INNER JOIN      articles
            ON          (articles.mediumid = media.mediumid)
        INNER JOIN      storedresults_articles
            ON          (storedresults_articles.articleid = articles.articleid)
        WHERE           storedresults_articles.storedresultid = %d
        ORDER BY        media.type
        """ % (storedresult,)
        return db.doQuery(qry)

    if field == "source+type":
        qry = """
        SELECT DISTINCT media.mediumid, media.name, media.sourcetypeid, media.type
        FROM            media
        INNER JOIN      articles
            ON          (articles.mediumid = media.mediumid)
        INNER JOIN      storedresults_articles
            ON          (storedresults_articles.articleid = articles.articleid)
        WHERE           storedresults_articles.storedresultid = %d
        ORDER BY        media.name
        """ % (storedresult,)
        return db.doQuery(qry)

    if field == "alternativebrands":
        alternatives = []

        try:
            brands = {}
            lines = open("/home/jpakraal/app/amcat/projects/scraping/merkenlijst_EDIT.csv").readlines()
            for line in lines:
                split = line.strip().split(',')
                brands[split[0].lower()] = split
            
            alternatives = brands[customer.lower()]
        except:
            alternatives = [customer]

        return alternatives

    if field == "storedresult":
        values = db.doQuery("select storedresultid from storedresults where projectid=379")
        return values

    for datasource in datamodel._datasources:
        values = datasource.getPossibleValues(field)
        if values is not None: return values

    raise AttributeError(field)

def getArticleValue(article, field, db = None): 
    """
    article := article object from the amcatdatabase
    field := One of the properties of the article
    
    Returns the value of the given field for the given article
    """
    try: 
        y, w, d = article.date.iso_week
    except:
        pass
    functions = {
        "article": lambda a:a.id,
        "headline": lambda a:a.headline,
        "url": lambda a:a.url,
        "date": lambda a:a.date,
        "project": lambda a:a.batch.project,
        "batch": lambda a:a.batch,
        "source": lambda a:a.source,
        "year": lambda a:y,
        "week": lambda a:w,
        "day": lambda a:d
        }
    if field in functions:
        return functions[field](article)
    if field == "sourcetype":
        sourcetype = db.doQuery("select type from media where mediumid = "+str(article.source.id))
        return sourcetype
    if field == "sentiment":
        return db.getValue('select sentiment from articles_sentiment where articleid=%i' % article.id)

def getQuote(article, keyword, nwords):
    return "Dit mag dus niet meer"

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


if __name__ == '__main__':
    c = ConceptTable(["a","b","c"], [[1,2,3],[4,5,6]])
    import cPickle
    print cPickle.dumps(c)
    
        

    
