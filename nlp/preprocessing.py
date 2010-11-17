from __future__ import with_statement

###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

"""
NLP Preprocessing of documents

AmCAT Preprocessing
===================

The strategy in AmCAT for preprocessing is generally:

1. Split the article in sentences
2. Create a 'preprocessing job' of analysisid and sentenceids
   in the jobs table 
3. Run the preprocessing job, which inserts preprocessing results
   in the jobs table as pickled raw data
4. Store the results into the parses_* tables

Generally, (1) and (2) run on user request. (3) can run offline and can
be outsourced and parallelized. (4) runs periodically in a single thread
to avoid locking/simultaneous insert problems.

The structure of the parses_jobs_sentences table is
- Analysisid - reference to a preprocessing analysis
- Sentenceid - reference to a sentence
- Assigned - date the job was assigned
- Started - boolean to control that a process has accepted the sentence
- Result - null if not completed, otherwise a pickled result

The pickled result should be a sequence of 2-tuples (description, result),
where description should be a string (such as 'tokens', 'triples'), and
result should be something that the storing procedure corresponding to the
description can use. The pickle should contain only primitive objects (string,
int, float, date) and built-in collections (list, tuple, set, dict)

Module contents
===============
The main entry point for this module are the following methods:

- assignSentences(db, sentences)
- assignArticles(db, articles)
- storeResults(db)
- splitArticles(db, articles)

In each case, the caller is responsible for committing the db transaction.
"""

from itertools import izip, count
import sbd, re, dbtoolkit, toolkit, traceback, article
import word
import tadpole
import alpino, lemmata
import table3, sentence
import sys, traceback
from analysis import Analysis
import cPickle as pickle
from amcatlogging import logExceptions
import logging; log = logging.getLogger(__name__)
import ticker

#import amcatlogging; amcatlogging.debugModule()

def _getid(o):
    return o if type(o) == int else o.id


###########################################################################
#                        Preprocessing management                         #
###########################################################################  

def assignSentences(db, analysis, sentences, check=True):
    """Assign the given sentences to be processed using the given analysis

    @type db: L{amcatDB} 
    @param db: A database connection- caller should commit.
    @type analysis: Analysis object or int
    @param analysis: The analysis to assign the sentences to
    @type sentences: Sentence objects or ints
    @param sentences: The sentences to be analysed
    @param check: If True, remove sentences that have already been analysed
    """
    sentenceids = set(_getid(s) for s in sentences)
    analysisid = _getid(analysis)
    if check: # remove already parsed
        SQL = """select distinct sentenceid from parses_words
                 where analysisid=%i and %s""" % (
            analysisid, db.intSelectionSQL("sentenceid", sentenceids))
        sentenceids -= set(db.getColumn(SQL))
    if not sentenceids: return
    # remove already assigned
    SQL = """select distinct sentenceid from parses_jobs_sentences
                 where analysisid=%i and %s""" % (
            analysisid, db.intSelectionSQL("sentenceid", sentenceids))
    sentenceids -= set(db.getColumn(SQL)) 
    db.insertmany("parses_jobs_sentences", ("analysisid", "sentenceid"),
                  [(analysisid, sid) for sid in sentenceids])
        

    
def storeResult(db, analysis, sid, result):
    analysisid = _getid(analysis)
    if type(result) <> str:
        result = pickle.dumps(result)
    result = dbtoolkit.quotesql(result)
    sql = """update parses_jobs_sentences set result=%s,done=1 where
             sentenceid=%i and analysisid=%i""" % (result, sid, analysisid)
    db.doQuery(sql)


###########################################################################
#                           Splitting articles                            #
###########################################################################    

def splitArticle(db, art):
    """Split the given article into sentences

    If article has sentences, will return silently

    @type db: L{amcatDB} 
    @param db: Connection to the database - caller should commit
    @type art: L{article.Article} 
    @param art: The article to split
    """
    if art.sentences: return False
    text = db.getText(art.id)
    if not text:
        toolkit.warn("Article %s empty, adding headline only" % art.id)
        text = ""
        text = re.sub(r"q11\s*\n", "\n\n",text)
    #if article.byline: text = article.byline + "\n\n" + text
    if art.headline: text = art.headline.replace(";",".")+ "\n\n" + text                                              
    spl = sbd.splitPars(text,  maxsentlength=2000, abbreviateIfTooLong=True)
    for parnr, par in izip(count(1), spl):
        for sentnr, sent in izip(count(1), par):
            sent = sent.strip()
            orig = sent
            [sent], encoding = dbtoolkit.encodeTexts([sent])
            if len(sent) > 6000:
                raise Exception("Sentence longer than 6000 characters, this is not normal!")
            db.insert("sentences", {"articleid":art.id, "parnr" : parnr, "sentnr" :
                                        sentnr, "sentence" : sent, 'encoding': encoding})
    art.removeCached("sentences")
    return True

###########################################################################
#                             Statistics                                  #
###########################################################################

def getStatistics(db):
    """return a Table with statistics on #assigned, #done etc per analysis"""
    SQL = """select analysisid, count(sentenceid) as [#assigned], count(started) as [#started],
                 sum(cast(done as int)) as [#done]
             from parses_jobs_sentences
             group by analysisid order by analysisid"""
    return db.doQueryTable(SQL)



def _filter(text):
    l = len(text.strip().split())
    return l > 1 and l < 30

def getNonemptySentenceTexts(db, analysis, maxn):
    """Retrieve and mark a number of sentences, deleting empties and returning id and text

    The result can be less than maxn if sentences were deleted. If there were no sentences to
    parse at all, will return None. If there were sentences, but all were deleted, returns []
    
    @param analysis: the Analysis object to get sentences from
    @param maxn: the maximum number of sentences to retrieve
    @return: a list of (sentenceid, text) pairs to be analysed, or None if the queue is empty
    """
    analysisid = _getid(analysis)
    todelete = set()
    result = []
    for sent in getSentences(db, analysis, maxn):
        text = sent.text.strip()
        nwords = len(text.split())
        if nwords <= 1 or nwords > 60:
            todelete.add(sent.id)
        else:
            result.append((sent.id, sent.text))
    if not (result or todelete): return None
    log.info("len(todelete)=%i, len(result)=%i" % (len(todelete), len(result)))
    db.doQuery("DELETE FROM parses_jobs_sentences WHERE analysisid=%i AND %s" % (analysisid, db.intSelectionSQL("sentenceid", todelete)))
    db.commit()
    return result

def getSentences(db, analysis, maxn):
    """Retrieve and mark a number of sentences to be analysed

    B{Important: This function will obtain a table lock on parses_jobs_sentences and
    commit as soon as they are marked, so make sure that the db does not contain
    any ongoing transactions you might want to rollback!}

    @param analysis: the Analysis object to get sentences from
    @param maxn: the maximum number of sentences to retrieve
    @return: a sequence of Sentence objects to be analysed
    """
    #Get eligible sentenceids, lock table, update 'started', commit
    analysisid = _getid(analysis)
    with db.transaction():
        SQL = """select top %(maxn)i sentenceid from parses_jobs_sentences 
              with (repeatableread,tablockx)
              where analysisid=%(analysisid)i and started is null and done=0 order by assigned """ % locals()
        sids = list(db.getColumn(SQL))
        if sids:
            SQL = ("update parses_jobs_sentences set started=getdate() where %s" %
                   db.intSelectionSQL("sentenceid", sids))
            db.doQuery(SQL)
    #Create and return sentence objects
    return (sentence.Sentence(db, sid) for sid in sids)

def reset(db, analysis):
    """Reset all non-completed sentences to non-started and call L{purge}"""
    analysisid = _getid(analysis)
    purge(db, analysis)
    db.doQuery("update parses_jobs_sentences set started=null where done=0")

def purge(db, analysis):
    """Remove all already-parsed articles from the parses_jobs_sentences table"""
    analysisid = _getid(analysis)
    SQL = "delete from parses_jobs_sentences where analysisid=%i and sentenceid in (select sentenceid from parses_words where analysisid=%i)" % (analysisid, analysisid)
    db.doQuery(SQL)
            
def save(db, analysis, maxn=None):
    """Save pickled parses to the perses_triples/parses_words tables and remove from parses_jobs

    @param maxn: if given, save maximum maxn sentences in one go. If not given, repeatedly
                 save sentences until all sentences are done
    """
    import amcatlogging; amcatlogging.infoModule()
    purge(db, analysis)
    analysisid = _getid(analysis)
    s = _ParseSaver(db, analysis.id)
    if maxn:
        s.saveResults(maxn)
    else:
        s.saveAll()
        
###########################################################################
#                           Convenience methods                           #
###########################################################################    
    
def assignArticles(db, analysis, articles, commitarticle=True):
    """Convenience method to L{splitArticle} and L{assignSentences}

    If the underlying methods call exceptions, they are logged using
    L{amcatlogging.exception}.

    @type db: L{amcatDB} 
    @param db: Connection to the database - caller should commit
    @type analysis: int or L{analysis.Analysis}
    @param analysis: The analysis to assign them to
    @type articles: ints or L{article.Article}s
    @param articles: The articles to assign
    """
    for art in ticker.tickerate(articles, detail=1):
        with logExceptions():
            if type(art) == int: art = article.Article(db, art)
            splitArticle(db, art)
            assignSentences(db, analysis, art.sentences)
            if commitarticle: db.commit()
            
def splitArticles(db, articles):
    """Split multiple articles into sentences

    If the underlying methods call exceptions, they are logged using
    L{amcatlogging.exception}.

    @type db: L{amcatDB} 
    @param db: Connection to the database - caller should commit
    @type articles: ints or L{article.Article}s
    @param articles: The articles to split
    """
    nsplit = 0
    for art in articles:
        with logExceptions():
            if type(art) == int: art = article.Article(db, art)
            nsplit += int(bool(splitArticle(db, art)))
    return nsplit

class _ParseSaver(object):
    """Helper object to save results from the jobs table to the parses_* tables"""
    
    def __init__(self, db, analysis):
        """
        @param db: The connection. NOTE: the saveResults (and saveAll) methods will run a transaction
                   on this connection, so make sure not to have pending updates on it
        @param analysis: the analysis object or id
        """
        self.db = db
        self._words_cache = None
        if type(analysis)==int: analysis=Analysis(self.db, analysis)
        self.analysis = analysis

    @property
    def _words(self):
        if self._words_cache is None:
            self._words_cache = word.CachingWordCreator(language=self.analysis.language, db=self.db)
        return self._words_cache
    
    def saveTokens(self, sentenceid, tokens):
        """Save the given token tuples on the given sentence in the  parses_words table, making words as needed"""
        seen = set()
        for token in tokens:
            position, word, lemma, poscat, posmajor, posminor = token
            if position in seen:
                log.debug("Already seen position %i (seen=%s), setting new position: %i" % (position, seen, max(seen)+1))
                position = max(seen) + 1
            seen.add(position)

            if position >= 256:
                log.warn("Ignoring token with  position >= 256! (%i.%i %r)" % (sentenceid, position, token))
                continue
                
            wordid = self._words.getWord(word, lemma, poscat)
            posid = self._words.getPos(posmajor, posminor, poscat)
            log.debug(str([self.analysis.id, sentenceid, position, position, wordid, posid]))
            self.db.insert("parses_words", dict(sentenceid=sentenceid, wordbegin=position, 
                                                posid=posid, wordid=wordid, 
                                                analysisid=self.analysis.id), 
                           retrieveIdent=False)
    def saveTriples(self, sentenceid, triples):
        """Save the given triple tuples on the given sentence in the  parses_triples table, making rels as needed"""
        for parentpos, rel, childpos in triples:
            relid = self._words.getRel(rel)
            self.db.insert("parses_triples", dict(sentenceid=sentenceid, parentbegin=parentpos, 
                                                  childbegin=childpos, relation=relid, 
                                                  analysisid=self.analysis.id), 
                           retrieveIdent=False)

    def saveResults(self, n=100, sids = None):
        """Save n results from the jobs table to the parses_* tables.
        This method *will* run and commit/rollback a transaction on self.db
        This method internally calls saveTriples/saveTokens"""
        log.debug("Querying max %i sentences from analysis %i" % (n, self.analysis.id))
        SQL = """SELECT top %i sentenceid, result FROM parses_jobs_sentences WHERE analysisid=%i
                 AND done=1""" % (n, self.analysis.id)
        if sids:
            SQL += " AND (%s)" % (self.db.intSelectionSQL("sentenceid", sids))
        todelete = []
        data = self.db.doQuery(SQL)
        log.debug("Retrieved %i sentences to save" % len(data))
        with self.db.transaction():
            for sid, result in data:
                result = pickle.loads(result)
                for rtype, result in result:
                    if rtype == "tiples": rtype = "triples"
                    if rtype == "tokens": self.saveTokens(sid, result)
                    elif rtype == "triples": self.saveTriples(sid, result)
                    else:
                        raise ValueError("Unknown result type: %s" % (rtype))
                todelete.append(sid)
            log.debug("Deleting %i sentences" % len(todelete))
            if todelete:
                SQL = "DELETE FROM parses_jobs_sentences WHERE analysisid=%i AND %s" % (
                    self.analysis.id, self.db.intSelectionSQL("sentenceid", todelete))
                self.db.doQuery(SQL)
        log.debug("Saved and deleted sentences %r" % todelete)
        return todelete
        
    def saveAll(self, npercommit=500):
        """Repeatedly save results from the jobs table to the parses_* tables until done.
        This method internally calls saveResults, which *will* run transactions on self.db"""
        log.debug("Querying database for N")
        SQL = "select count(*) from parses_jobs_sentences where analysisid=%i and done=1" % self.analysis.id
        n = self.db.getValue(SQL)
        done = 0
        log.info("%i sentences to save" % n)
        
        while True:
            with logExceptions(log):
                sids = self.saveResults(npercommit)
                if not sids: break
                done += len(sids)
                log.info("%i sentences saved, %i/%i done (%1.1f%%)" % (len(sids), done, n, float(done)/n*100))
                

        

if __name__ == '__main__':
    import dbtoolkit, article
    import amcatlogging; amcatlogging.setStreamHandler()
    amcatlogging.debugModule()
    db  = dbtoolkit.amcatDB()
    sids = set(toolkit.intlist())
    _ParseSaver(db, 3).saveResults(len(sids), sids)
