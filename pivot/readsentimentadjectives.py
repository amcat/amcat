import dbtoolkit, sys, random

file = open("sentiment-adj.txt")
db = dbtoolkit.amcatDB()
lines = file.readlines()
startwords = sys.maxint

sentmap = {
    'positive' : 100,
    'negative' : -100,
    'neutral'  : 0,
    'posneg'   : 0,
}


#sql = "select * from words_lemmata where pos = 'A'" 
#res = db.doQuery(sql)

for nr, line in enumerate(lines):
    line = line.strip("\n")
    confidence, lemma, pos, sentiment  = line.split("/")

    if confidence == "cf-score":
        continue
        
    confidence = int(float(confidence.replace(",",".")) * 100)
    sentiment = sentmap[sentiment]
    print sentiment

    sql = "select lemmaid from words_lemmata where lemma = '%s' AND pos = 'A'" %(lemma)
    lid = db.getValue(sql)
    if not lid:
        lid = db.insert("words_lemmata", dict(lemma=lemma, pos='A', celex=0,languageid=2))
        print "Creatied new lemma %i for %s" % (lid, lemma)

    print "Inserting %s / %i / %s / %s" % (lemma, lid, sentiment, confidence)
    db.insert("words_sentiment", dict(lemmaid=lid, sentiment=sentiment, confidence=confidence), retrieveIdent=False)
    

db.conn.commit()
