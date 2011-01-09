from amcat.tools import toolkit
from amcat.tools.cachable.cachable import Cachable, DBProperty, DBProperties
from amcat.tools.cachable.latebind import LB

def clean(s):
    return toolkit.clean(s,1,1)

class Medium(Cachable):
    __table__ = 'media'
    __idcolumn__ = 'mediumid'
    __labelprop__ = 'name'

    name, circulation, type, abbrev = DBProperties(4)
    language = DBProperty(LB("Language"))
    

class Media(object):

    
    def clean(self, s):
        if type(s) == str: s = s.decode("latin-1")
        return toolkit.clean(s,1,1)
    def __init__(self, db):
        self.db = db
        self.names = {}
        self.aliasses = {}
        for medium in Medium.all(self.db):
            self.names[self.clean(medium.name)] = medium
    def lookupName(self, name):
        return self.names.get(self.clean(name))
