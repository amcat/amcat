import dbtoolkit, draftdatamodel, ontologydatasource, amcatxapian, anydbm

fileDBM = '/home/roblalau/dev/dbm/wordfrequency.db'

def save():
    db = dbtoolkit.amcatDB()
    dm = draftdatamodel.getDatamodel(db)
    words = map(str, list(ontologydatasource.getDescendants(dm.brand.getObject(config['data_association_oid']), 3)))
    idx = amcatxapian.Index(config['data_index'], db)
    ###FIXME
    # Should probably do some locking here.
    dbm = anydbm.open(fileDBM, 'n')
    for word in words:
        results = len(list(idx.query(word)))
        dbm[word.lower()] = str(results)
    dbm.close()
