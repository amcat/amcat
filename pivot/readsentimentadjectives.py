import dbtoolkit, sys

file = open("sentiment-adj.txt")
db = dbtoolkit.amcatDB()
lines = file.readlines()
startwords = sys.maxint
for nr, line in enumerate(lines):
    line = line.strip("\n")
    line = line.split("/")
    if line[0] == "cf-score": 
        print line ## create table here
        startwords = nr 
    if startwords < nr:
        print line[0] ## insert lines into database
        confidence = int(float(line[0])*100)
        print confidence
        sql = "insert into words_sentiment ( lemmaid, sentiment, confidence ) values (%s, %s, %s)" % (line[1], line[3], confidence)
        db.doInsert(sql)
        #
file.close()
