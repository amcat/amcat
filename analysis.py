from cachable2 import Cachable, DBProperty
import language

class Analysis(Cachable):
    """Object representing an NLP 'preprocessing' analysis"""
    __table__ = 'parses_analyses'
    __idcolumn__ = 'analysisid'
    label = DBProperty()
    language = DBProperty(language.Language)

    
