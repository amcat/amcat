import dbtoolkit
from cachable import Cachable, DBPropertyFactory
from functools import partial
import article

class Sentence(Cachable):
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'text'

    __dbproperties__ = ["parnr", "sentnr", "encoding"]
    text = DBPropertyFactory("isnull(longsentence, sentence)", objfunc=article.decode)
    article = DBPropertyFactory("articleid", dbfunc=article.doCreateArticle)
    
if __name__ == '__main__':
    s = Sentence(dbtoolkit.amcatDB(),280600)
    print s.parnr, s.sentnr, s.text
    print `s.article`
