from datasource import DataSource, FunctionalDataModel, FunctionalMapping, Field, Identity
from functools import partial
from mst import getSolution
from aggregator import Aggregator
import table2

def getter(mapdict, b, reverse=False):
    if reverse:
        for k, v in mapdict.items():
            if v == b: 
                yield k
    else:
        v = mapdict.get(b)
        if v: yield v

class SillyDataSource(DataSource):
    def __init__(self, label, mapdict):
        self.label = label
        mappings = []
        for a in mapdict:
            for b in mapdict[a]:
                fielda = Field(self, a)
                fieldb = Field(self, b)
                mapper = partial(getter, mapdict[a][b])
                reversemapper = partial(getter, mapdict[a][b], reverse=True)
                mapping = FunctionalMapping(fielda, fieldb, mapper, reversemapper)
                mappings.append(mapping)
        
        DataSource.__init__(self, 
                            mappings)
    def getData(self, field, input):
        pass
    def __str__(self): return self.label
    def __repr__(self): return self.label
    
                


AMCAT_DB = { "article": {"date" : {"a1" : 40, "a2" :34}, 
                         "medium" : {"a1" : 'vk', "a2" : 'nrc'}}}
LUCENE_DB = {"hit" : {"article" : {"h1" : "a1", "h2" : "a1", "h3" : "a2"},
                      "nhits" : {"h1" : 4, "h2" : 7, "h3" : 12}}}

dm = FunctionalDataModel(getSolution)
dm.register(SillyDataSource("AMCAT", AMCAT_DB))
dm.register(SillyDataSource("LUCENE", LUCENE_DB))

filters = { "date" : [40, 34]  }
state = dm.getRoute("date", "nhits")
                  
ag = Aggregator(state.getEdges(), filters)

n = ag.getData()
print " | ".join(map(lambda x: "%-15s" % x, n.fields))
print "-+-".join(["-"*15 for x in n.fields])
for row in n.data:
    print " | ".join(map(lambda x: "%-15s" % x, row))

            
