import dbtoolkit, sys

arg = sys.argv[1]
if arg[0] == "s":
    srid = int(arg[1:])
    where = " articleid in (select articleid from storedresults_articles where storedresultid=%i)" % srid
else:
    projectid = int(sys.argv[1])
    where = " batchid in (select batchid from batches where projectid=%i)" % projectid

print "Querying for duplicate articles"

db = dbtoolkit.anokoDB()
db.doQuery("create table #tempmax (n int not null, mx int not null)")

N=[3,4,5]

for i in N:
    SQL = """insert into #tempmax
    select %i,  max(articleid) from articles
    where %s
    and articleid not in (select mx from #tempmax)
    group by mediumid, date, section, headline, pagenr
    having count(*) > 2""" % (i, where)
    print SQL
    db.doQuery(SQL)

cols = ", ".join('a%i' % i for i in N)
SQL = """select t1.n, t1.a1, t1.a2, %s from (
  select min(articleid) as a1, max(articleid) as a2, count(*) as n from articles
  where %s
  group by mediumid, date, section, headline, pagenr
  having count(*) > 1
) t1""" % (cols, where)

for i in N:
    t = "t%i" % i
    a = "a%i" % i
    SQL += """  left join (
    select min(articleid) as a1, max(articleid) as %(a)s from articles
    where %(where)s
    and articleid not in (select mx from #tempmax where n <= %(i)s)
    group by mediumid, date, section, headline, pagenr
    having count(*) > 1
    ) %(t)s on t1.a1 = %(t)s.a1""" % locals()

print "\n\n", SQL
data = db.doQuery(SQL)

db.doQuery("drop table #tempmax")
db.conn.commit()

print "%i duplicates found" % len(data)

NN = 500
for j in range(0, len(data), NN):
    k = j+NN
    if k > len(data): k = len(data)-1
    print "Processing duplicates %i - %i" % (j, k)
    d2 = data[j:k]
    aids = set()
    coded = set()
    prep = set()
    for n, a1, a2, a3, a4, a5 in d2:
        aids |= set([a1, a2, a3, a4, a5])
        
    print "Obtaining use in annotations, indices, storedresults, parses etc."
    SQL = """select distinct a.articleid, ca.articleid, s.articleid, s2.articleid, s3.articleid from articles a
        left  join codingjobs_articles ca on ca.articleid = a.articleid
        left join sentences s on s.articleid = a.articleid
        left join sentences s2 on s2.articleid = a.articleid and s2.sentenceid in (select sentenceid from parses_words)
        left join storedresults_articles s3 on s3.articleid = a.articleid
        where a.articleid in (%s)""" % (",".join(str(i) for i in aids))
    for a, ca, s, s2, s3 in db.doQuery(SQL):
        if ca: coded.add(a)
        elif s or s2 or s3: prep.add(a)

    delarts = set()
    totarts = 0
    for n, a1, a2, a3, a4, a5 in d2:
        n=5
        as = [a1, a2]
        if a3 <> a2: as.append(a3)
        if a4 <> a2: as.append(a4)
        if a5 <> a2: as.append(a5)
        totarts += len(as)
        cands = [x for x in as if x not in coded]
        if len(cands) <> len(as):
            pass
        else:
            ok = False
            for i,a in enumerate(cands[:]):
                if a in prep:
                    del(cands[i])
                    ok = True
                    break
            if not ok:
                cands = cands[1:]

        if len(as) - len(cands) <> 1:
            print len(as), len(cands)
        delarts |= set(cands)
    print "deleting %i/%i articles for %i uniques..." % (len(delarts), totarts, len(d2))
    db.doQuery("delete from articles where articleid in (%s)" % (",".join(str(i) for i in delarts)))
    db.conn.commit()

            
        
        
        
        
