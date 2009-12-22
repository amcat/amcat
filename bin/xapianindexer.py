import amcatxapian, sys, dbtoolkit, toolkit

if len(sys.argv) <= 1:
    toolkit.warn("Usage: python amcatxapian.py INDEXLOC [QUERY] [< ARTICLEIDS]\n\nIf QUERY is giving, query exsting index; otherwise, build new index from ARTICLEIDS")
    sys.exit(1)
    
indexloc = sys.argv[1]
query = " ".join(sys.argv[2:])
if query.strip():
    toolkit.warn("Querying index %s with %r" % (indexloc, query))
    i = amcatxapian.Index(indexloc, dbtoolkit.amcatDB())
    for a, weight in i.query(query, returnWeights=True):
        print a.id, weight
else:
    toolkit.warn("Creating new xapian index (database) at %s" % indexloc)
    articles = toolkit.tickerate(toolkit.intlist())
    i = amcatxapian.createIndex(indexloc, articles, dbtoolkit.amcatDB())
    toolkit.warn("Created index %s" % i)

