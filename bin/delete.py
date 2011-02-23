"""python delete.py [-p]< ARTICLEIDS

Deletes the given articles in small batches

if -p is given, delete project 2 ("prullenbak") and remove batches, etc as well
"""

import sys
import logging; log = logging.getLogger(__name__)

from amcat.tools import toolkit
from amcat.tools.logging import amcatlogging; amcatlogging.setup()
amcatlogging.debugModule()
from amcat.db import dbtoolkit

BATCHSIZE = 100
db = dbtoolkit.amcatDB()

if "-p" in sys.argv:
    log.info("Selecting articles to delete from project 2")
    aids = list(db.getColumn("select top 200 articleid from vw_tmp_articles where projectid=2"))
else:
    log.info("Reading article IDS from standard input")
    aids = list(toolkit.intlist())

log.info("%i articles to delete" % len(aids))

def delete(table, where):
    log.debug("Deleting from table {table} where {where}".format(**locals()))
    i = db.getValue("select count(*) from {table} where {where}".format(**locals()))
    log.debug("Will delete {i} rows".format(**locals()))
    sql = "delete from {table} where {where}".format(**locals())
    db.doQuery(sql)
    db.commit()


    
fks = [# table, fkname, cols, reftable, refcols
    ("parses_triples", "FK_parses_triples_parses_words", "sentenceid, analysisid, parentbegin", "parses_words", "sentenceid, analysisid, wordbegin"),
    ("parses_triples", "FK_parses_triples_parses_words1", "sentenceid, analysisid, childbegin", "parses_words", "sentenceid, analysisid, wordbegin"),
    ("parses_words", "FK_parses_sentences", "sentenceid", "sentences", "sentenceid"),
    ]

for table, fkname, cols, reftable, refcols in fks:
    log.info("Dropping FK constraint {table}.{fkname}".format(**locals()))
    sql = "alter table {table} drop {fkname}".format(**locals())
    try:
        db.doQuery(sql)
    except Exception, e:
        if "s not a constraint" in str(e):
            log.info("Constraint did not exist")
        else:
            raise
    else:
        db.commit()

try:
    for aids in toolkit.splitlist(aids, itemsperbatch=BATCHSIZE):
        log.info("Deleting %i articles" % len(aids))
        where = db.intSelectionSQL("articleid", aids)
        # delete tables linked to sentences
        for table in "parses_words", "parses_triples", "net_arrows","codedsentences":
            twhere = "sentenceid in (select sentenceid from sentences where {where})".format(**locals())
            delete(table, twhere)
        # delete tables linked to codedarticles
        for table in "net_arrows","codedsentences", "articles_annotations", "antwerpen_articles_annotations":
            twhere = "codingjob_articleid in (select codingjob_articleid from codingjobs_articles where {where})".format(**locals())
            delete(table, twhere)
        # delete (tables linked to) articles
        for table in "codingjobs_articles", "sentences", "storedresults_articles", "articles":
            delete(table, where)

finally:
    for table, fkname, cols, reftable, refcols in fks:
        log.info("Creating FK constraint {table}.{fkname}".format(**locals()))
        
        SQL="""ALTER TABLE {table}
               ADD CONSTRAINT {fkname}
               FOREIGN KEY({cols})
               REFERENCES {reftable} ({refcols})
               ON DELETE NO ACTION 
               ON UPDATE NO ACTION""".format(**locals())
        db.doQuery(SQL)
        db.commit()

log.info("Done!")
