import dbtoolkit
from cachable import Cachable, DBPropertyFactory, DBFKPropertyFactory
from functools import partial
import article, word

class Sentence(Cachable):
    __table__ = 'sentences'
    __idcolumn__ = 'sentenceid'
    __labelprop__ = 'text'
    __dbproperties__ = ["parnr", "sentnr", "encoding"]
    __encodingprop__ = 'encoding'
    
    text = DBPropertyFactory("isnull(longsentence, sentence)", decode=True)
    article = DBPropertyFactory("articleid", dbfunc=article.doCreateArticle)
    words = DBFKPropertyFactory("parses_words", "wordid", dbfunc=word.Word)
    
if __name__ == '__main__':
    s = Sentence(dbtoolkit.amcatDB(),30031005)
    print " ".join("%s/%s" % (w.lemma, w.lemma.pos) for w in  s.words)
