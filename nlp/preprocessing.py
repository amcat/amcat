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
import sbd, re, dbtoolkit, toolkit, amcatwarning, traceback, article
import tadpole
import alpino, lemmata
import sys, traceback

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
        

    
def storeResults(db, analysis):
    pass


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
            db.insert("sentences", {"articleid":art.id, "parnr" : parnr, "sentnr" : sentnr, "sentence" : sent, 'encoding': encoding})
    art.removeCached("sentences")
    return True

###########################################################################
#                           Convenience methods                           #
###########################################################################    
    
def assignArticles(db, analysis, articles):
    """Convenience method to L{splitArticle} and L{assignSentences}

    If the underlying methods call exceptions, they are issues as
    L{amcatwarning.Error} warnings.

    @type db: L{amcatDB} 
    @param db: Connection to the database - caller should commit
    @type analysis: int or L{analysis.Analysis}
    @param analysis: The analysis to assign them to
    @type articles: ints or L{article.Article}s
    @param articles: The articles to assign
    """
    for art in articles:
        try:
            if type(art) == int: art = article.Article(db, art)
            splitArticle(db, article)
            assignSentences(db, analysis, art.sentences)
        except Exception, e:
            amcatwarning.Error(str(e)).warn()
            
def splitArticles(db, articles):
    """Split multiple articles into sentences

    If the splitting method raises exceptions, they are issues as
    L{amcatwarning.Error} warnings.

    @type db: L{amcatDB} 
    @param db: Connection to the database - caller should commit
    @type articles: ints or L{article.Article}s
    @param articles: The articles to split
    """
    nsplit = 0
    for art in articles:
        try:
            if type(art) == int: art = article.Article(db, art)
            nsplit += int(bool(splitArticle(db, art)))
        except Exception, e:
            amcatwarning.Error(traceback.format_exc()).warn()
    return nsplit

# def parseArticles(articles):
#     if type(articles) not in (tuple, list, set): articles = set(articles)
#     db = toolkit.head(articles).db
#     toolkit.ticker.warn("Splitting articles")
#     splitArticles(articles)
#     toolkit.ticker.warn("SEtting up lemmatiser")
#     lem = lemmata.Lemmata(db, alpino.ALPINO_ANALYSISID)
#     for article in toolkit.tickerate(articles, msg="Parsing", detail=1):
#         for sent in article.sentences:
#             alpino.parseAndStoreSentence(lem, sent)
#         article.db.commit()

if __name__ == '__main__':
    import dbtoolkit, article
    db  = dbtoolkit.amcatDB()
    sids = range(100, 200)
    assignSentences(db, 0, sids)
    db.commit()


