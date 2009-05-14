import toolkit

def clean(s):
    return toolkit.clean(s,1,1)

class Source(object):
    def __init__(self, id, name, circulation, language, type, abbrev):
        self.id = id
        self.name = clean(name)
        self.prettyname = toolkit.clean(name,1)
        self.circulation = circulation
        self.language = language
        self.type = type
        self.abbrev = abbrev
    def __str__(self):
        return self.name
    def __cmp__(self, other):
        if type(other) <> Source: return -1
        return cmp(self.id, other.id)

class Sources(object):
    def __init__(self, connection):
        self.index_name = {}
        self.sources = {}

        
        for id,name in connection.doQuery("select mediumid, name from media_dict"):
            self.index_name[clean(name)] = id
        try:
            data = connection.doQuery("select mediumid, name, circulation, language, type, isnull(abbrev, name) from media where mediumid>0")
        except:
            data = connection.doQuery("select mediumid, name, circulation, language, type, ifnull(abbrev, name) from media where mediumid>0")
            
        for info in data:
            source = Source(*info)
            self.index_name[source.name] = source.id
            self.sources[source.id] = source

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
