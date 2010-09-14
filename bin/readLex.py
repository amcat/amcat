#!/usr/bin/python

import re,toolkit, lexisnexis
import article
import dbtoolkit


if __name__ == '__main__':
    import sys, traceback, os
    #toolkit.setDebug()
    
    batchname = None
    commit = 1
    query=None

    for i, arg in enumerate(sys.argv[:5]):
        if arg.startswith("name="):
            batchname = arg[5:]
            del sys.argv[i]
            break
    for i, arg in enumerate(sys.argv[:5]):
        if arg.startswith("query="):
            query = arg[5:]
            del sys.argv[i]
            break
    for i, arg in enumerate(sys.argv[:5]):
        if arg == "--commit":
            commit = 1
            del sys.argv[i]
            break
    for i, arg in enumerate(sys.argv[:5]):
        if arg == "--test":
            commit = 0
            del sys.argv[i]
            break

    if len(sys.argv) < 2:
        print """
        Usage: readLex [--test] PROJECTID [name=BATCHNAME] [query==QUERY] [FILENAMES]
        Creates new batch with the given name and inserts the listed files.
        Be sure to use quotes if using multiword BATCHNAME.

        Only checks whether the files can be read if --test is specified. This
        is advised the first time you import a new source or language.

        if no FILENAMES are specified, reads FILENAMES from standard input
        imports all articles in FILENAMES into articles with batchid=BATCHID
        """
        sys.exit(1)

    projectid = int(sys.argv[1])
    db = dbtoolkit.anokoDB()

    if len(sys.argv) == 2:
        filenames = [x.rstrip("\n") for x in sys.stdin.readlines()]
    else:
        filenames = sys.argv[2:]

    # extract query from first file

    if not batchname:
        if "_" in filenames[0]:
            batchname = os.getcwd().split('/')[-1] + '/' + filenames[0][:filenames[0].index("_")]
        else:
            batchname = os.getcwd().split('/')[-1] + '/' + filenames[0]

    print "Starting readLex with projectid=%s, name=%s of %s files" % (projectid, batchname, len(filenames))
    if not commit: 
        print "Only checking validity of input, rerun without --test to actually insert!"


    files = map(open, filenames)
    n, batches, errors, errorcount = lexisnexis.readfiles(db, projectid, batchname, files, True, commit, fixedquery=query)
    if errors:
        print "Errors:", errors

    print "Committing ..."

    db.conn.commit()

    print "Succesfully read %i articles in %i batches from %i files" % (n, len(batches), len(filenames))
