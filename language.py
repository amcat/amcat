from cachable2 import Cachable, DBProperty, ForeignKey
import user

class Language(Cachable):
    __table__ = 'languages'
    __idcolumn__ = 'languageid'
    
    label = DBProperty()
    users = ForeignKey(lambda : User)