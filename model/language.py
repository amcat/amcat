from amcat.tools.cachable.cachable import Cachable, DBProperty


class Language(Cachable):
    __table__ = 'languages'
    __idcolumn__ = 'languageid'
    
    label = DBProperty()

    
