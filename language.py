from cachable import Cachable

class Language(Cachable):
    __table__ = 'languages'
    __idcolumn__ = 'languageid'
    __dbproperties__ = ["label",]