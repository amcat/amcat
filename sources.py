import toolkit
from cachable import Cachable, CachingMeta, DBPropertyFactory
import time
import language

def clean(s):
    return toolkit.clean(s,1,1)

class Source(Cachable):
    __metaclass__ = CachingMeta
    __table__ = 'media'
    __idcolumn__ = 'mediumid'
    __labelprop__ = 'name'
    __dbproperties__ = ["name", "circulation", "type", "abbrev"]
    language = DBPropertyFactory("language", dbfunc = language.Language)

class Sources(object):
    def __init__(self, connection):
        self.index_name = {}
        self.sources = {}
        for id,name in connection.doQuery("select mediumid, name from media_dict"):
            self.addAlias(name, id)
        data = connection.doQuery("select mediumid from media where mediumid>0")
        for mediumid, in data:
            self.addSource(Source(connection, mediumid))
    def addAlias(self, alias, id):
        self.index_name[clean(alias)] = id
    def addSource(self, source):
        self.sources[source.id] = source
        self.addAlias(source.name, source.id)
    def lookupID(self, id):
        if id is None:
            return None
        elif id in self.sources:
            return self.sources[id]
        else:
            #print self.sources
            raise Exception("No source with id '%s'?" % id)
    def lookupName(self, source, lax=0):
        source = clean(source)
        if source in self.index_name:
            return self.sources[self.index_name[source]]
        else:
            if lax: return None
            raise Exception('Could not find source "%s"' % source)

    def name(self,id):
        src = self.lookupID(id)
        if src: return src.name
        else: return 'None'

    def asDict(self):
        res = {}
        for k,v in self.sources.items():
            res[k] = v.name
        return res
