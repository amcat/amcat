from datasource import DataSource, FunctionalDataModel, FunctionalMapping, Field, Identity
from functools import partial
from mst import getSolution
from aggregator import Aggregator

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
                         "medium" : {"a1" : 'vk', "a2" : 'vk'}}}
LUCENE_DB = {"hit" : {"article" : {"h1" : "a1", "h2" : "a1", "h3" : "a3"},
                      "nhits" : {"h1" : 4, "h2" : 7, "h3" : 12}}}

dm = FunctionalDataModel(getSolution)
dm.register(SillyDataSource("AMCAT", AMCAT_DB))
dm.register(SillyDataSource("LUCENE", LUCENE_DB))

state = dm.getRoute("date", "nhits")
print "\n\n\n%s" % state

print dm.getConcepts()

filters = { "date" : [40] , "nhits" : [4] }

for mapping in state.getEdges():
    print mapping
    print mapping.getCost()

ag = Aggregator(state.getEdges(), filters)

ag.getData()

            