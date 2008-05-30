import toolkit

def clean(s):
    return toolkit.clean(s,1,1)

class Source:
    def __init__(this, id, name, circulation, language, type, abbrev):
        this.id = id
        this.name = clean(name)
        this.prettyname = toolkit.clean(name,1)
        this.circulation = circulation
        this.language = language
        this.type = type
        this.abbrev = abbrev
    def __str__(this):
        return this.name

class Sources:
    def __init__(this, connection):
        this.index_name = {}
        this.sources = {}
        
        for id,name in connection.doQuery("select mediumid, name from media_dict"):
            this.index_name[clean(name)] = id
        for info in connection.doQuery("select mediumid, name, circulation, language, type, isnull(abbrev, name) from media where mediumid>0"):
            source = Source(*info)
            this.index_name[source.name] = source.id
            this.sources[source.id] = source

    def lookupID(this, id):
        if id is None:
            return None
        elif id in this.sources:
            return this.sources[id]
        else:
            #print this.sources
            raise Exception("No source with id '%s'?" % id)

    def lookupName(this, source, lax=0):
        source = clean(source)
        if source in this.index_name:
            return this.sources[this.index_name[source]]
        else:
            if lax: return None
            raise Exception('Could not find source "%s"' % source)

    def name(this,id):
        src = this.lookupID(id)
        if src: return src.name
        else: return 'None'

    def asDict(this):
        res = {}
        for k,v in this.sources.items():
            res[k] = v.name
        return res
