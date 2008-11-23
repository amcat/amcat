import sys
#sys.path.insert(0,'/home/amcat/libpy-dev')
import amcatXml, dbtoolkit


def err():
    sys.stderr.write("""
Usage: readXML PROJECTID BATCHNAME [FILENAMES]
  Creates new batch with the given name and inserts the listed files.
  Be sure to use quotes if using multiword BATCHNAME.

  if no FILENAMES are specified, reads FILENAMES from standard input
  imports all articles in FILENAMES into articles with batchid=BATCHID

""")
    sys.exit(1)
            

if __name__=='__main__':
    if len(sys.argv) < 3: err()
    fn = sys.argv[3:]
    if not fn: fn = sys.stdin.readlines()
    db = dbtoolkit.anokoDB()
    articleCount, batchid, errors, errorCount = amcatXml.readfiles(db, sys.argv[1], sys.argv[2], fn)
    if articleCount > 0:
        print 'Finished adding %s articles to batch %s' % (articleCount, batchid)
    print "Error count: ", errorCount
