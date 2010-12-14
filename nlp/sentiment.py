import collections
import word, sentence, toolkit, article
from analysis import Analysis
from cachable2 import cache
import re

class Token(object):
    def __init__(self, word, topic=None, sentiment=None, intensity=None, notes=None):
        self.word = word
        self.topic = topic
        self.sentiment = sentiment
        self.intensity = intensity
        self.notes = notes
    def __str__(self):
        return "Token(word=(%i:%i %s),topic=%s,sentiment=%s,intensity=%s,notes=%s)" % (
            self.word.sentence.id, self.word.position, self.word.word.lemma, self.topic, self.sentiment, self.intensity, self.notes)

def search(max):
    """Return [0, 1, -1, 2, -2, .... -max]"""
    return list(toolkit.flatten(zip(range(max+1), range(0,-(max+1),-1))))[1:]

def searchtokens(tokens, i, pattern):
    for pos in pattern:
        j = i + pos 
        if j < 0: continue
        if j >= len(tokens): continue
        if tokens[j].word.sentence <> tokens[i].word.sentence: continue
        yield j, tokens[j]

    
class Sentiment(object):

    def __init__(self, lexicon, analysis, topicdict={}, db=None):
        if type(lexicon) == int: lexicon = word.SentimentLexicon(db, lexicon)
        if type(analysis) == int: analysis = Analysis(db, analysis)
        self.lexicon = lexicon
        self.analysis = analysis
        self.ldict = lexicon.lemmaidDict()
        self.topicdict = topicdict

    def getTokens(self, *sents):
        cache(sents, words=dict(word=dict(lemma=dict(lemma=["string"]))))

        sls = set()
        for sent in sents:
            for w in sent.words:
                sl =self.ldict.get(w.word.lemma.id)
                if sl: sls.add(sl)

        cache(sls, ['sentiment','intensity'])

        for sent in sents:
            for w in sent.words:
                l = w.word.lemma
                sl = self.ldict.get(l.id)
                topic = self.topicdict.get(l.id)
                sent = sl and sl.sentiment
                intensity = sl and sl.intensity
                notes = sl and sl.notes
                yield Token(w, topic, sent, intensity, notes)
            

    def spreadTopics(self, tokens):
        originaltopics = [t.topic for t in tokens] 
        for i, token in enumerate(tokens):
            if token.topic: continue
            for j, token2 in searchtokens(tokens, i, search(2)):
                topic = originaltopics[j]
                if topic:
                    token.topic = topic
                    break
            
    def resolveIntensifiers(self, tokens):
        for i, token in enumerate(tokens):
            if token.intensity:
                for j, token2 in searchtokens(tokens, i, search(2)):
                    if token2.sentiment:
                        token2.sentiment *= token.intensity
                        break
                token.intensity = None

    def resolveConditions(self, tokens):
        for i, token in enumerate(tokens):
            if not token.notes: continue
            m = re.match('topic=([^;]+)', token.notes)
            if m:
                topics = m.groups()[0].split(",")
                if token.topic not in topics:
                    token.sentiment = None
                token.notes = None
                continue
            m = re.match('previous=([^;]+)', token.notes)
            if m:
                previous = m.groups()[0].split(",")
                if not any(str(token2.word.word.lemma) in previous
                           for (j, token2) in searchtokens(tokens, i, [-1, -2])):
                    token.sentiment = None
                token.notes = None
                    
                    
                
    def sentimentsPerTopic(self, tokens):
        result = collections.defaultdict(list)
        for t in tokens:
            if t.sentiment:
                if t.topic:
                    result[t.topic].append(t.sentiment)
                result[None].append(t.sentiment)
        return result

    def totalSentiments(self, tokens):
        sents = []
        for t in tokens:
            if t.sentiment: sents.append(t.sentiment)
        return self.computeSentiment(sents)

    def resolveSpecial(self, tokens):
        for i, token in enumerate(tokens):
            # 'mag/moet/kan beter'
            if token.word.word.lemma.pos=='A' and str(token.word.word).endswith('er'):
                for pos in [-1, -2]:
                    j = i + pos 
                    if j < 0: continue
                    if tokens[j].word.sentence <> token.word.sentence: continue
                    if tokens[j].word.word.lemma.pos=='V' and str(tokens[j].word.word.lemma) in ['kunnen','mogen','moeten']:
                        token.sentiment = -1
                        break

    
    def computeSentiment(self, sentiments):
        if not sentiments: return None
        return sum(sentiments) / sum(abs(s) for s in sentiments)



    def getResolvedTokensForArticle(self, article):
        sents = [s.getAnalysedSentence(self.analysis.id) for s in article.sentences]
        tokens = list(self.getTokens(*sents))
        self.spreadTopics(tokens)
        self.resolveIntensifiers(tokens)
        self.resolveConditions(tokens)
        self.resolveSpecial(tokens)
        return tokens

    def getSentimentPerTopicForArticle(self, article):
        tokens = self.getResolvedTokensForArticle(article)
        for topic, sents in self.sentimentsPerTopic(tokens).iteritems():
            yield topic, self.computeSentiment(sents)
        
if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    aid = 59074552

    topicdict = dict(db.doQuery("select lemmaid, topic from tmp_olery_topics"))
    s = Sentiment(2, 3, topicdict, db)

   
    for topic, sentiment in s.getSentimentPerTopicForArticle(article.Article(db, aid)):
        print topic, sentiment
