"""
Query Engine
"""

import operation, mst, tabulatorstate
import os, time, sys
import toolkit
import table3, tableoutput
import filter, aggregator # not used, import to allow indirect access
import enginebase
import logging; log = logging.getLogger(__name__)
    
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

class QueryEngine(enginebase.QueryEngineBase):
    def __init__(self, datamodel, db, log=False, profile=False, debug=toolkit.ticker.warn):
        enginebase.QueryEngineBase.__init__(self, datamodel, log, profile)
        self.operationsFactory = operation.OperationsFactory()
        self.debug = debug
        self.db = db

    def getList(self, concepts, filters, sortfields=None, limit=None, offset=None, distinct=False):
        T0 = time.time()
        route = getRoute(self.model, concepts, filters)
        state = tabulatorstate.State(None, route, filters, distinct)
        self.debug("Starting reduction, concepts=%s, filters=%s" % (concepts, filters))
        while state.solution is None:
            op = self.operationsFactory.getBestOperation(state, debug=self.debug)
            #toolkit.ticker.warn("Reducing...")
            state = op.apply(state)
            #toolkit.ticker.warn("Cleaning...")
            clean(state, concepts)
        self.debug("Done, %i results" % (len(state.solution.data)))
        solution = getColumns(state.solution, concepts)

        if distinct: solution = list(makedistinct(solution))
        T1 = time.time()
        t = enginebase.ConceptTable(concepts,solution)
        postprocess(t, sortfields, limit, offset)

        if type(self.profile) == list:
            T9 = time.time()
            self.profile.append([tostr(concepts), tostr(filters), tostr(sortfields, sort=True), limit, offset, T1-T0, T9-T1])
        return t


    def getQuote(self, art, *args, **kargs):
        #import dbtoolkit
        #article.db = dbtoolkit.amcatDB()
        import article
        if type(art) == int: art = article.Article(self.db, art)
        log.info('Calling Article object for quote %s' % args)
        kargs['quotelen'] = 7
        kargs['boldfunc'] = lambda w : "<strong>%s</strong>" % w
        q = art.quote(*args, **kargs)
        if not q:
            toolkit.warn("No quote for article %r, args=%s, kargs=%s" % (art, args, kargs))
            return " ".join(art.words()[:25]) + " .."
        return q
        


    
def getRoute(model, concepts, filters):
    concepts = set(concepts) | set(f.concept for f in filters)
    return mst.getSolution(model.getMappings(), concepts)

def getColumns(node, goal):
    if not node.data or node.fields == goal: return node.data
    indices = map(node.fields.index, goal)
    result = []
    for row in node.data:
        result.append(tuple(map(lambda i: row[i], indices)))
    return result


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

        

    
