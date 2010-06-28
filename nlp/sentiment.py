import toolkit, sentence, article, cachable




SENTIMENT_SQL = """
select p.sentenceid, wordbegin, sentiment, confidence, intensifier from parses_words p inner join words_words w on p.wordid = w.wordid
inner join wva.words_sentiment s on w.lemmaid = s.lemmaid
 %s
 where %s
-- and p.analysisid=3
 and ((intensifier <>0) or (sentiment <> 0) or (confidence <> 0))
order by  p.sentenceid, wordbegin
"""
SENTIMENT_SQL = """
select p.sentenceid, wordbegin, sentiment, intensifier from parses_words p 
inner join tmp_sentwords w on p.wordid = w.wordid
where sentenceid in (select sentenceid from sentences where %s)
"""



INTENSIFIER_RANGE = 4
CACHE_WORD = False
class SentimentSentence(sentence.Sentence):
    def __init__(self, *args, **kargs):
        sentence.Sentence.__init__(self, *args, **kargs)
        if CACHE_WORD:
            self.cacheWords()
        self.sentimentTokens = {}
    def addToken(self, wordbegin, *args, **kargs):
        if wordbegin >= len(self.words):
            #HACK!
            word = self.words[-1]
        else:
            word = self.words[wordbegin]
        self.sentimentTokens[wordbegin] = SentimentToken(word, *args, **kargs)
    def getIntensifiers(self, position):
        for i in range(max(0, position-INTENSIFIER_RANGE), position):
            t = self.sentimentTokens.get(i)
            if t and t.intensification: yield t
    def getSentiment(self, pos=None):
        sent = 0.0
        for position, t in self.sentimentTokens.iteritems():
            s = t.sentiment# * t.confidence
            if s:
                for i in self.getIntensifiers(position):
                    s *= i.intensification
            if pos is not None:
                if pos and s > 0: sent += s
                elif (not pos) and s < 0: sent -= s
            else:
                sent += s
        return sent
    def toHTML(self):
        html = ''
        for i, word in enumerate(self.words):
            t = self.sentimentTokens.get(i)
            if t:
                html += t.toHTML(list(self.getIntensifiers(i)))
            else:
                html += "%s " % word.label
        return html

def getHSV(sent, conf=1):
    h = .167 + .167*sent
    s = conf
    b = 1
    return h,s,b
def getcol(sent, conf=1):
    return toolkit.HSVtoHTML(*getHSV(sent, conf))
    
class SentimentToken(object):
    def __init__(self, word, sentiment, intensification):
        self.word = word
        self.sentiment = sentiment
        self.intensification = intensification
    def toHTML(self, intensifiers=[]):
        sent = self.sentiment
        for i in intensifiers: sent *= i.intensification
        styles = []
        txt = ''
        if sent:
            txt += "Total=%+1.1f, from sent=%+1.1f" % (sent, self.sentiment)
            styles.append("background: %s" % getcol(sent))
            if intensifiers: txt+= " modifiers %s" % (
                ",".join("%s/%+1.1f" % (i.word, i.intensification) for i in intensifiers))
        if self.intensification:
            styles.append("border: 2px solid %s" % getcol(self.intensification))
            txt += " Is modifier: %+1.1f" % self.intensification
        return "<span style='%s' title='%s'>%s</span> " % (";".join(styles), txt, self.word)
        
def getSentimentSentences(db, where, tick=True, restrict=True):
    #extrajoin = ""
    #if "storedresultid" in where: extrajoin = "inner join sentences z on z.sentenceid=p.sentenceid inner join storedresults_articles a on z.articleid = a.articleid"
    #elif "articleid" in where: extrajoin = "inner join sentences z on z.sentenceid=p.sentenceid "
    SQL = SENTIMENT_SQL % where#(extrajoin, where)
    if restrict: SQL += " AND analysisid=3"
    #toolkit.ticker.warn("Querying database\n%s" % SQL)
    data = db.doQuery(SQL)
    sids = set(row[0] for row in data)
    sentences = dict((sid, SentimentSentence(db, sid)) for sid in sids)
    #sentence.cacheWords(sentences.values())
    cursent = None
    if tick: data = toolkit.tickerate(data, detail=1)
    for sid, pos, sent,  intens in data:
        sentences[sid].addToken(pos, sent/100., intens/100.)
    return sentences.values()


if __name__ == '__main__':
    import dbtoolkit
    db = dbtoolkit.amcatDB(profile=True)
    where = "sentenceid in (35101048,35101049,35101050,22317334)"
    html = open('/home/amcat/www/plain/test/sentiment.html', 'w')
    html.write("<html><table border=1>\n")
    
    #where = "storedresultid = 763"
    articles = {}
    for s in getSentimentSentences(db, where):
        aid = s.article.id
        a = articles.get(aid)
        if not a:
            a = article.Article(db, aid)
            a.cacheProperties("source","date")
            articles[aid] = a
        print a.id, a.date.date, a.source.id, s.getSentiment()
        html.write("<tr><td>%s</td><td>%s</td><td>%+1.2f</td><td>%s</td></tr>\n" % (
            s.article.id, s.id, s.getSentiment(), s.toHTML()))
    html.write("</table></html>")
    import sys; 
    db.printProfile(stream=sys.stderr)
    
