import re
from pySesameDB import SesameDBConnection, Error, InterfaceError
from logger import log

def aggSum(x, y, finalize=False):
    if finalize: return x
    if not x: return float(y)
    return x+float(y)
    
def aggAvg(x, y, finalize=False):
    if finalize: return float(x[0]) / x[1]
    if not x:
        return (y,1)
    return x[0]+y, x[1]+1


def aggCount(x, y, finalize=False):
    if finalize: return x
    if not x: return 1
    return x+1

aggrfuncs = {'sum':aggSum,
         'avg':aggAvg,
         'count':aggCount}

class AggregateSesameDBConnection(SesameDBConnection):
    def __init__(self, *args, **kargs):
        self.super = super(AggregateSesameDBConnection, self)
        self.super.__init__(*args, **kargs)

    def execute(self, query, returnHeader=0, params=None):
        if params: query = query % params
	aq = AggregateQuery(query)
	if not aq.isAggregate:
            return self.super.execute(query, returnHeader=returnHeader)
	else:
            data = aq.execute(self.super)
            if returnHeader:
                return data, aq.header
            else:
                return data
connect = AggregateSesameDBConnection

class AggregateQuery(object):
    def __init__(self, SeRQL):
        log.write("Initializing query:\n%s"%SeRQL)
        self.selectfields = [] # infield names that need to be selected
        self.groupby = []      # infield indexes for grouping
        self.header = []       # outfield names for output
        self.output = []       # for each outfield: infieldindex, aggrfunc_or_None
        
        fields, groupby, pre, post = self.parse(SeRQL)
        
        if groupby:
            self.selectfields = re.split(r"\s*,\s*", groupby )
            self.groupby = list(range(len(self.selectfields))) # groupby at start selectfields

        self.isAggregate = self.interpretSelect(fields)
        self.query = pre + ", ".join(self.selectfields) + post
        log.write("Parsed query")

    def execute(self, dbconn):
        log.write("Executing query")
        data = dbconn.execute(self.query)
        log.write("Executed query!")
        agg = self.aggregate(data)
        log.write("Aggregated results!")
        return agg

    def aggregate(self, results):
        aggrow = {} # new rows of keyset : values
        for row in results:
            key = tuple(row[field] for field in self.groupby)
            if not key in aggrow: aggrow[key] = [None]*len(self.output)
            values = aggrow[key]
            
            for i, (srcfield, func) in enumerate(self.output):
                if func:
                    values[i] = func(values[i], row[srcfield]) 
                else:
                    values[i] = row[srcfield]

        #finalize
        log.write("Made first pass, finalizing")
        result = []
        for key in sorted(aggrow.keys()):
            vals = aggrow[key] 
            row = []
            for (srcfield, func), val in zip(self.output, vals):
                if func:
                    row.append(func(val, None, finalize=1))
                else:
                    row.append(val)
            result.append(row)
        
        return result


    def parse(self,SeRQL):
        m = re.search(r'(SELECT\s+)(.*?)(\s+FROM\s+.*)\s+GROUP BY\s+(\w+(?:\s*,\s*\w+)*)(.*)',SeRQL, re.DOTALL | re.I)
        if m:
            fieldstr = m.group(2)
            groupbystr = m.group(4)
            pre = m.group(1)
            post =m.group(3) + m.group(5)
        else:
            m= re.search(r'(SELECT\s+)(.*?)(\s+FROM\s+.*)',SeRQL, re.DOTALL | re.I)
            if m:
                fieldstr = m.group(2)
                groupbystr = None
                pre = m.group(1)
                post = m.group(3)
            else:
                raise ParseError('Cannot parse query:\n%s' % SeRQL)
        return fieldstr, groupbystr, pre, post

    def ingroupby(self, label):
        if label not in self.selectfields: return False
        if self.selectfields.index(label) in self.groupby: return True
        return False

    def interpretSelect(self, fieldstr):
        aggr = bool(self.groupby)
        unaggrfields = []

        fields = re.split(r'\s*,\s*', fieldstr)
        for field in fields:
            if re.match('\w+$',field):
                if not self.ingroupby(field): unaggrfields.append(field)
                func = None
                asfield = field
                srcfield = field
            else:
                m = re.match('(\w+)\((\w+)\)( as (\w+))?',field, re.I)
                if not m: raise ParseError('Cannot parse field "%s"\nfields=%s' % (field,fields))
                try:
                    func = aggrfuncs[m.group(1).lower()]
                except KeyError:
                    raise ParseError("Unknown aggregate function '%s'" % m.group(1))
                srcfield = m.group(2)
                asfield = m.lastindex>2 and m.group(4) or srcfield
                aggr = True
            
            if srcfield not in self.selectfields:
                self.selectfields.append(srcfield)
            srcindex = self.selectfields.index(srcfield)
            self.header.append(asfield)
            self.output.append((srcindex, func))

        if aggr and unaggrfields:
            raise ParseError("Fields %s are not in group by or aggregate function" % `unaggrfields`)

        return aggr


if __name__ == '__main__':
    

    SeRQL='''SELECT S, Count(Q) as W, Avg(Q) as Q FROM
    {{Subject} T {Object}} net:inArticle {umts:article_17072423};
    net:quality {Q},
    {Subject} serql:directType {ont:Reality} rdfs:label {S},
    {Object} serql:directType {} rdfs:label {O}
    GROUP BY S,O
    using namespace
    owl = <http://www.w3.org/2002/07/owl#>,
    net = <http://www.cs.vu.nl/~wva/net#>,
    xsd = <http://www.w3.org/2001/XMLSchema#>,
    ont = <http://www.cs.vu.nl/~wva/politics.owl#>,
    umts = <http://www.cs.vu.nl/~wva/umts#>
    '''

    print "Testing aggregate parsing..."

    print SeRQL.split("\n")[0]

    q = AggregateQuery(SeRQL)
    print q.query.split("\n")[0]
    print 'Select %s' % q.selectfields
    print 'Group by %r' % q.groupby
    print 'Header %s' % q.header
    print 'output:'
    for var, func in q.output:
        print var, func

    print "Executing aggregate..."
    conn = connect('http://prauw.cs.vu.nl:8080/sesame', 'wouter','maanbrem', repository='anoko')
    conn.namespaces = {'owl' : 'http://www.w3.org/2002/07/owl#',
                       'ont' : 'http://www.cs.vu.nl/~wva/politics.owl#',
                       'xsd' : 'http://www.w3.org/2001/XMLSchema#',
                       'net' : 'http://www.cs.vu.nl/~wva/net#'}
    
    SeRQL='SELECT M FROM {} net:year {"2004"^^xsd:int}; net:month {M}'
    print SeRQL
    print conn.execute(SeRQL)
    SeRQL='SELECT M,Count(M) AS C, SUM(M) as D FROM {} net:year {"2004"^^xsd:int}; net:month {M} GROUP BY M'
    print SeRQL
    print conn.execute(SeRQL, returnHeader=1)

    
    

class ParseError(InterfaceError):
    pass
