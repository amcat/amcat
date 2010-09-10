import dbtoolkit, sys, toolkit

frm = int(sys.argv[1])


SQL = """SELECT s.sentenceid, sentence
FROM sentences_parses p
INNER JOIN sentences s
ON p.sentenceid = s.sentenceid
WHERE started = 0
AND parsejobid=%i""" % frm

db = dbtoolkit.anokoDB()
dsids, ssids = [], []
for sid, sent in db.doQuery(SQL):
    sent = sent.strip()
    if " " in sent: continue
    if sent == '[PICTURE]' or sent == '[DUMMY]':
        dsids.append(sid)
    else:
        ssids.append(sid)

if dsids:
    print "Moving %i [DUMMY] sentences to -99" % len(dsids)
    for sub in toolkit.splitlist(dsids, 1000):
        ids = ",".join(str(i) for i in sub)
        db.doQuery("UPDATE sentences_parses SET parsejobid=-99 WHERE parsejobid=%i AND sentenceid IN (%s) AND sentenceid not in (select sentenceid from sentences_parses where parsejobid=-99)" % (frm, ids))
        db.doQuery("DELETE FROM sentences_parses WHERE parsejobid=%i AND sentenceid IN (%s) AND sentenceid in (select sentenceid from sentences_parses where parsejobid=-99)" % (frm, ids))

if ssids:
    print "Moving %i single-word sentences to -1" % len(ssids)
    for sub in toolkit.splitlist(ssids, 1000):
        ids = ",".join(str(i) for i in sub)
        db.doQuery("UPDATE sentences_parses SET parsejobid=-1 WHERE parsejobid=%i AND sentenceid IN (%s) AND sentenceid not in (select sentenceid from sentences_parses where parsejobid=-1)" % (frm, ids))
        db.doQuery("DELETE FROM sentences_parses WHERE parsejobid=%i AND sentenceid IN (%s) AND sentenceid in (select sentenceid from sentences_parses where parsejobid=-1)" % (frm, ids))


    
        
        
