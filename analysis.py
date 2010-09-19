import cachable, language

class Analysis(cachable.Cachable):
    __metaclass__ = cachable.CachingMeta
    __table__ = 'parses_analyses'
    __idcolumn__ = 'analysisid'
    __dbproperties__ = ['label']
    language = cachable.DBPropertyFactory("languageid", dbfunc = language.Language)
