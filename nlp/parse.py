from __future__ import with_statement
import toolkit
from contextlib import contextmanager

AMCAT_RESOURCES = "/home/amcat/resources"
AMCAT_HOSTNAME = 'amcat'
ALT_RESOURCES = "/home/wva/resources"
def getResourcesDir():
    import socket
    if socket.gethostname() == AMCAT_HOSTNAME:
        return AMCAT_RESOURCES
    else:
        return ALT_RESOURCES

class Parser(object):
    analysisid = None
    def stop(self): pass
    def start(self): pass
    def parse(self, sentence): abstract

def getParsers():
    import alpino, stanford
    return [alpino.AlpinoParser,
            stanford.StanfordParser]
def getParser(id):
    return toolkit.head(p for p in getParsers() if p.analysisid == id)
def getParserForLanguage(language):
    import analysis
    return toolkit.head(p for p in getParsers()
                        if language == analysis.Analysis(language.db, p.analysisid).language)

@contextmanager
def managedParser(parser, *args, **kargs):
    p = None
    try:
        p = parser if isinstance(parser, Parser) else parser(*args, **kargs)
        p.start()
        yield p
    finally:
        if p is not None:
            p.stop()

def parseSentence(sentence, parser=None):
    if not parser:
        if type(sentence) in (str, unicode):
            raise Exception("Need either parser (name) or db Sentence object")
        parser = getParserForLanguage(sentence.article.source.language)
    if not parser:
        raise Exception("Cannot find parser for %s" % sentence)
    if type(sentence) not in (str, unicode): sentence = sentence.text
    with managedParser(parser) as p:
        return p.parse(sentence)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        toolkit.warn("Usage: alpino.py SID [PARSER]\nOr:    parser.py PARSER SENTENCE")
        sys.exit()
    try:
        sid = int(sys.argv[1])
    except:
        if len(sys.argv) < 2:
            toolkit.warn("Usage: alpino.py SID [PARSER]\nOr:    parser.py PARSER SENTENCE")
            toolkit.warn("If first argument is not a number, two arguments (parser + sentence) are required")
            sys.exit()
        sid = None

    if sid:
        import dbtoolkit, sentence
        db = dbtoolkit.amcatDB()
        sent = sentence.Sentence(db, sid)
        parser = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        parser = sys.argv[1]
        sent = " ".join(sys.argv[2:])
    print list(parseSentence(sent, parser))
