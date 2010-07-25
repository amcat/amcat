"""
Parse Storer - stores parsed sentences in the AmCAT parses_words and _triples tables

Expected input: pickled sequence of 2-tuples containing sentenceid and parse, where
parse is a sequence of 3-tuples (parent, relation, child), where relation
is a string from parses_rels and parent and child are 'token tuples' containing
the arguments needed for the lemmata.Token constructor
(position, word, lemma, poscat, posmajor, posminor='') (position int, others str)
"""

POSITION_INDEX = 0

import lemmata, toolkit, word
import cPickle as pickle

def tokensFromTriples(triples):
    yielded = set()
    for parent, rel, child in triples:
        for token in parent, child:
            pos = token[POSITION_INDEX]
            if pos in yielded: continue
            yielded.add(pos)
            yield lemmata.Token(*token)
            
def triplesFromTriples(triples):
    for parent, rel, child in triples:
        parentpos = parent[POSITION_INDEX]
        childpos = child[POSITION_INDEX]
        yield parentpos, rel, childpos
        
class ParseStorer(object):
    def __init__(self, db, analysisid):
        self.db = db
        self._words = None
        self.analysisid = analysisid

    @property
    def words(self):
        if self._words is None:
            language = db.getValue("select languageid from parses_analyses where analysisid=%i" % (self.analysisid))
            self._words = word.CachingWordCreator(language=language, db=self.db)
        return self._words
    
    def getWord(self, token):
        return self.words.getWord(token.word, token.lemma, token.poscat)
    def getRel(self, rel):
        return self.words.getRel(rel)
        
    def getWord(self, token):
        return self.words.getWord(token.word, token.lemma, token.poscat)
    
    def storeTriples(self, sentenceid, triples):
        for token in tokensFromTriples(triples):
            wordid = self.words.getWord(token.word, token.lemma, token.poscat)
            posid = self.words.getPos(token.posmajor, token.posminor, token.poscat)
            self.db.insert("parses_words", dict(sentenceid=sentenceid, wordbegin=token.position, posid=posid, wordid=wordid, analysisid=self.analysisid), retrieveIdent=False)
        self.db.commit()
        for parentpos, rel, childpos in triplesFromTriples(triples):
            relid = self.words.getRel(rel)
            self.db.insert("parses_triples", dict(sentenceid=sentenceid, parentbegin=parentpos, childbegin=childpos, relation=relid, analysisid=self.analysisid), retrieveIdent=False)
        #toolkit.warn("Stored parses_* for sentence %i" % sentenceid)

    def storePickle(self, picklestream):
        for sid, triples in pickle.load(picklestream):
            self.storeTriples(sid, triples)
            
    def storeResults(self):
        SQL = "DELETE FROM parses_jobs_sentences WHERE analysisid=%i AND sentenceid in (select sentenceid from parses_words where analysisid=%i)" % (
            self.analysisid, self.analysisid)
        
        while True:
            SQL = "SELECT TOP 100 sentenceid, result FROM parses_jobs_sentences WHERE analysisid=%i AND result is not null " % (self.analysisid,)
            results = self.db.doQuery(SQL)
            if not results:
                toolkit.warn("No results: done!")
                return
            toolkit.ticker.warn("Fetched %i results" % len(results))
            
            for sid, result in results:
                triples = pickle.loads(result)
                try:
                    self.storeTriples(sid, triples)
                    self.db.doQuery("DELETE FROM parses_jobs_sentences WHERE analysisid=%i AND sentenceid=%i" % (self.analysisid, sid))
                    #toolkit.warn("Stored %i triples for sentence %i" % (len(triples), sid))
                    self.db.commit()
                except Exception, e:
                    toolkit.warn("Exception on storing result for %i: \n%s" % (sid, e))
                    self.db.rollback()
            
if __name__ == '__main__':
    import sys, dbtoolkit
    
    if len(sys.argv) <> 2:
        toolkit.warn("USAGE: paython parsestorer.py ANALYSISID"+__doc__)
        sys.exit()

    analysisid = int(sys.argv[1])

    db = dbtoolkit.amcatDB()
    p = ParseStorer(db, analysisid)

    p.storeResults()
            

        
    
