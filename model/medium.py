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
    

