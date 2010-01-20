import amcatxapian, sys, dbtoolkit, toolkit

db = dbtoolkit.amcatDB()

if len(sys.argv) <= 1:
    toolkit.warn("Usage: python amcatxapian.py INDEXLOC [-nXX] [QUERY] [< ARTICLEIDS]\n\nIf QUERY is given, query exsting index; otherwise, build new index from ARTICLEIDS. -g determines one or more term generators: 1-4 for n-grams, b for brouwers, s for brouwers-supercat")
    sys.exit(1)

def getGenerator(x):
    if x in "123456789":
        return amcatxapian.NGramGenerator(int(x))
    if x == "b":
        return amcatxapian.BrouwersGenerator(db)
    if x == "s":
        return amcatxapian.BrouwersGenerator(db, "scat")
    raise Exception(x)
       
indexloc = sys.argv[1]
if len(sys.argv) > 2 and sys.argv[2].startswith("-n"):
    generators = map(getGenerator, sys.argv[2][2:])
    del(sys.argv[2])
else:
    generators = None

    
query = " ".join(sys.argv[2:])
if query.strip():
    toolkit.warn("Querying index %s with %r" % (indexloc, query))
    i = amcatxapian.Index(indexloc, db)
    for a, weight in i.query(query, returnWeights=True):
        print a.id, weight
else:
    toolkit.warn("Creating new xapian index (database) at %s, generators=%s" % (indexloc, generators))
    articles = toolkit.tickerate(toolkit.intlist())
    i = amcatxapian.createIndex(indexloc, articles, db, termgenerators=generators)
    toolkit.warn("Created index %s" % i)

docs = list(i.articles)
#print list(i.getFrequencies()), docs, list(i.getFrequencies(docs[0]))
