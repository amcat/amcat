import dbtoolkit, sys, random

file = open("sentiment-adj.txt")
db = dbtoolkit.amcatDB()
lines = file.readlines()
startwords = sys.maxint

#sql = "select * from words_lemmata where pos = 'A'" 
#res = db.doQuery(sql)

for nr, line in enumerate(lines):
    line = line.strip("\n")
    line = line.split("/")
    if line[0] == "cf-score": 
        startwords = nr 
    if startwords < nr:
        confidence = int(float(line[0].replace(',','.'))*100)
        sentiment = None
        if line[3] == 'positive':
            sentiment = 100
        elif line[3] == 'negative':
            sentiment = -100
        elif line[3] == 'neutral':
            sentiment = 0
        else:
            sentiment = 0
        sql = "select * from words_lemmata where lemma = '%s' AND pos = 'A'" %(line[1])
        res = db.doQuery(sql)
        randomvalue = None
        if res:
            insertintodb = "insert into words_sentiment values (%s, %s, %s)"% (res[0][0], sentiment, confidence)
            db.doInsert(insertintodb)
        else:
            randomvalue = random.randint(250000,251000)
            insertintodb = "insert into words_lemmata values (%s, %s, 'A',1,2)"% (randomvalue,line[1],sentiment)
            insertsentiment = "insert into words_sentiment values (%s, %s, %s)"% (randomvalue, sentiment, confidence)

file.close()
