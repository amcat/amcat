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
import tadpole
import alpino, lemmata
import table3, sentence
import sys, traceback
from analysis import Analysis
import cPickle as pickle
from amcatlogging import logExceptions
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
    # remove already assigned
    SQL = """select distinct sentenceid from parses_jobs_sentences
                 where analysisid=%i and %s""" % (
            analysisid, db.intSelectionSQL("sentenceid", sentenceids))  
    sentenceids -= set(db.getColumn(SQL)) 
    db.insertmany("parses_jobs_sentences", ("analysisid", "sentenceid"),
                  [(analysisid, sid) for sid in sentenceids])
        

    
def storeResult(db, analysis, sid, result):
    analysisid = _getid(analysis)
    result = dbtoolkit.quotesql(result)
    sql = """update parses_jobs_sentences set result=%s where
             sentenceid=%i and analysisid=%i""" % (result, sid, analysisid)
    print sql
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
    SQL = """select analysisid, count(sentenceid) as [#assigned], min(assigned) as [oldest assigned],
                 max(assigned) as [youngest assigned], count(started) as [#started],
                 sum(case when result is null then 0 else 1 end) as [#done]
             from parses_jobs_sentences
             group by analysisid order by analysisid"""
    return db.doQueryTable(SQL)


def getSentences(db, analysis, maxn):
    """Retrieve and mark a number of sentences to be analysed

    B{Important: This function will obtain a table lock on parses_jobs_sentences and
    commit as soon as they are marked, so make sure that the db does not contain
    any ongoing transactions you might want to rollback!}

    @param analysis: the Analysis object to get sentences from
    @param maxn: the maximum number of sentences to retrieve
    @return: a list of Sentence objects to be analysed
    """
    #Get eligible sentenceids, lock table, update 'started', commit
    analysisid = _getid(analysis)
    with db.transaction():
        SQL = """select top %(maxn)i sentenceid from parses_jobs_sentences 
              with (repeatableread,tablockx)
              where analysisid=%(analysisid)i and started is null and result is null order by assigned """ % locals()
        sids = list(db.getColumn(SQL))
        if sids:
            SQL = ("update parses_jobs_sentences set started=getdate() where %s" %
                   db.intSelectionSQL("sentenceid", sids))
            db.doQuery(SQL)
    #Create and return sentence objects
    return (sentence.Sentence(db, sid) for sid in sids)

def reset(db, analysis):
    """Reset all non-completed sentences to non-started"""
    analysisid = _getid(analysis)
    db.doQuery("update parses_jobs_sentences set started=null where result is null")

###########################################################################
#                           Convenience methods                           #
###########################################################################    
    
def assignArticles(db, analysis, articles):
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
    for art in articles:
        with logExceptions():
            if type(art) == int: art = article.Article(db, art)
            splitArticle(db, art)
            assignSentences(db, analysis, art.sentences)
            
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

class ParseStorer(object):
    def __init__(self, db, analysis):
        self.db = db
        self._words = None
        if type(analysis)==int: analysis=Analysis(self.db, analysis)
        self.analysis = analysis

    @property
    def words(self):
        if self._words is None:
            self._words = word.CachingWordCreator(language=self.analysis.language, db=self.db)
        return self._words
    
    def getWord(self, token):
        return self.words.getWord(token.word, token.lemma, token.poscat)
    def getRel(self, rel):
        return self.words.getRel(rel)

    def storeTokens(self, sentenceid, tokens):
        print tokens
        for token in tokens:
            position, word, lemma, poscat, posmajor, posminor = token
            wordid = self.words.getWord(word, lemma, poscat)
            posid = self.words.getPos(posmajor, posminor, poscat)
            print wordid, posid, token
    def storeTriples(self, sentenceid, triples):
        return
        for token in tokensFromTriples(triples):
            wordid = self.words.getWord(token.word, token.lemma, token.poscat)
            posid = self.words.getPos(token.posmajor, token.posminor, token.poscat)
            self.db.insert("parses_words", dict(sentenceid=sentenceid, wordbegin=token.position, posid=posid, wordid=wordid, analysisid=self.analysisid), retrieveIdent=False)
        self.db.commit()
        for parentpos, rel, childpos in triplesFromTriples(triples):
            relid = self.words.getRel(rel)
            self.db.insert("parses_triples", dict(sentenceid=sentenceid, parentbegin=parentpos, childbegin=childpos, relation=relid, analysisid=self.analysisid), retrieveIdent=False)
        #toolkit.warn("Stored parses_* for sentence %i" % sentenceid)

    def storeResultsFromDB(self, sids):
        SQL = "SELECT sentenceid, result FROM parses_jobs_sentences WHERE analysisid=%i AND %s" % (
            self.analysis.id, self.db.intSelectionSQL("sentenceid", sids))
        for sid, result in self.db.doQuery(SQL):
            with logExceptions():
                result = pickle.loads(result)
                for rtype, result in result:
                    if rtype == "tiples": rtype = "triples"
                    if rtype == "tokens": self.storeTokens(sid, result)
                    elif rtype == "tiples": self.storeTriples(sid, result)
                    else:
                        raise ValueError("Unknown result type: %s" % (rtype))


if __name__ == '__main__':
    import dbtoolkit, article
    db  = dbtoolkit.amcatDB()
    ParseStorer(db, 2).storeResultsFromDB([44499901])

