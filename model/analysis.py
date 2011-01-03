from amcat.tools.cachable.latebind import LB
from amcat.tools.cachable.cachable import Cachable, DBProperty


class Analysis(Cachable):
    """Object representing an NLP 'preprocessing' analysis"""
    __table__ = 'parses_analyses'
    __idcolumn__ = 'analysisid'
    label = DBProperty()
    language = DBProperty(LB("Language"))

    
