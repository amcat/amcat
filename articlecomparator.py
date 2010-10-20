
import dbtoolkit, article, toolkit, sys, re, sbd
import split, datetime, preprocessing


db  = dbtoolkit.amcatDB()

class ArticleComparator(object):
   """Abstract Base Class that represents a method to compare articles"""

   def compareALL(self, articles1, articles2):
       raise NotImplementedError("Comparator subclasses should implement this method!")

   def compareArticles(self, art1, art2, alreadysplit=False):
       """ Compare two articles

       @param art1, art2: an articleid (integer)
       @return: a float indicating the similarity, from 0 to 1
       """
       for dummy, dummy2, score in self.compareAll([art1], [art2]):
           return score

   def findBestMatch(self, art, articles, alreadysplit=False):
       #return toolkit.best(art, articles, self.compareArticles) 
       score = 0
       for vergart in articles:
          s = self.compareArticles(art,vergart)
          if s > score:
             score = s
             bestmatch = vergart
       if score == 0:
          print '--------BESTMATCH IS ZERO'
          bestmatch, score = 0000, 0
       return bestmatch, score
          

class OverlapComparator(ArticleComparator):
   """Abstract class that compares articles by computing an overlap in features"""


   def compareAll(self, articles1, articles2, alreadysplit=False):
       """ When comparing sets of articles, compareALL first stores features in a dictionary {articlids: features}, so that features do not need to be computed more than once
       
       @param articles1, articles2: a list of articleids
       @param alreadysplit: if False, all articles will be preprocessed first (if unprocessed articles are used, overlapscores will be unreliable)
       @return: articleid1, articleid2 and the overlap
       """
       if not alreadysplit:
          db  = dbtoolkit.amcatDB()
          allarts = list(set(articles1) | set(articles2))
          preprocessing.splitArticles(db, allarts)                
       featuresdict1 = self.featuresdict(articles1)
       featuresdict2 = self.featuresdict(articles2)
       for art1 in featuresdict1:
           f1 = featuresdict1[art1]
           for art2 in featuresdict2:
               f2 = featuresdict2[art2]
               yield art1, art2, self.featuresOverlap(f1, f2)

   def featuresOverlap(self, f1, f2):
       """ Calculates the overlap of features (number of overlapping features divided by total number of features)

       @param f1, f2: a set of features
       @return: the overlap of the features
       """
       if (f1 or f2) == set(): print '\n\n ------------------------ WARNING ---------------------------- \n EMPTY NGRAMSETS. TRY PREPROCESSING \n\n'
       return float(len(f1 & f2)) / len(f1 | f2)

   def featuresdict(self, artlist):
       """ Generates a dictionary with articleids as keys and features as values

       @param artlist: list of articleids
       @return: a dictionary with articleids as keys and features as values
       """
       featuresdict={}
       for artid in artlist:
           art=article.Article(db,artid)
           features = set(self.getFeatures(art))
           featuresdict[artid] = features
       return featuresdict
    
   def getFeatures(self, art):
       raise NotImplementedError("OverlapComparator subclasses should implement this method!")

class NGramComparator(OverlapComparator):
    def __init__(self, n=1):
        """ n = the desired length of the n-grams (n=3 -> trigrams) """
        self.n = n

    def getFeatures(self, art):
        """ Generates the n-grams for each sentence of an article

        @param art: an article object
        @return: a list of strings, the n-grams tied together with underscores (['word1_word2_word3','word2_word3_word4']
        """
        sentencelist = self.sentlist(art.sentences)
        ngr = []
        for sentence in sentencelist:
            ngrams=self.parssent(sentence)
            ngr = ngr + ngrams
        return ngr

    def sentlist(self, sents, inkorten=False):
        """ Transforms a sentences object to a list containing strings of the sentences of an article. Also allowing data specific adjustments to the text
    
        @param sents: sentences object
        @return: a list containing strings of the sentences of an article
        """
        result = []
        sents = set(sents)
        for sent in sents:
            s = safestr(sent.text)
            result.append(str(s.strip()))
        return result

    def parssent(self, sentence):
        """ Generates the n-grams of a sentence

        @param sentence: a string
        @return: a list of strings, the n-grams tied together with underscores (['word1_word2_word3','word2_word3_word4']
        """
        l=[]
        result=[]
        for w in sentence.split(" "):
            l.append(w)
            if len(l)==self.n:
                result.append("_".join(l))
                del(l[0])
        return result   

def bestMatchInPeriod(art, articles, days=1, alreadysplit=False):
   comp = NGramComparator(n=3)
   articles = daysAfter(art, articles, days)
   return comp.findBestMatch(art, articles, alreadysplit)

def bestMatchPerSource(art, articles, alreadysplit=False):
   comp = NGramComparator(n=3)
   sdict = sourceDict(articles)
   for s in sdict:
      bestmatch, score = comp.findBestMatch(art, sdict[s], alreadysplit)
      if bestmatch == 0000: continue 
      yield s, bestmatch, score

def bestMatchPerSourceInPeriod(art, articles, days=1, alreadysplit=False):
   comp = NGramComparator(n=3)
   articles = daysAfter(art, articles, days)
   sdict = sourceDict(articles)
   for s in sdict:
      bestmatch, score = comp.findBestMatch(art, sdict[s], alreadysplit)
      if bestmatch == 0000: continue 
      yield s, bestmatch, score
      
def daysAfter(art, articles, days=1):
   """ reduces the list of 'articles' to only the articles that are published in a set period ('days') after the publication of 'art'

   @param art: an articleid (integer)
   @param articles: a list of articleids
   @param days: period in days after publication of art (days=1 is the day directly after art)
   @return: list of articleids that are published in a set period ('days') after the publication of 'art'
   """
   art=article.Article(db,art)
   artdate = datetime.date(art.date.year, art.date.month, art.date.day)
   relevant = []
   for aid in articles:
      a = article.Article(db,aid)
      adate = datetime.date(a.date.year, a.date.month, a.date.day)
      if not ((adate - artdate).days > days) and not ((adate - artdate).days < days): relevant.append(aid) 
   return relevant

def sourceDict(aiddata):
   """ creates a dictionary out of a list of articleids in which the keys are the sources and the values are the articleids (in a list)

   @param aiddata: a list of articleids
   @return: a dictionary out of a list of articleids in which the keys are the sources and the values are the articleids (in a list)
   """
   sourcedict = {}
   for aid in aiddata:
      source = article.Article(db,aid).source
      if not source in sourcedict: sourcedict[source] = [aid]
      else: sourcedict[source].append(aid)
   return sourcedict

def safestr(x):
    if type(x) == str: x = str.decode("latin-1")
    if type(x) <> unicode: x = unicode(x)
    return x.encode("ascii","replace")


