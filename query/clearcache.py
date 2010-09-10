import toolkit

def dropTable(db, table):
    if not db.hasTable(table): return
    toolkit.warn("Dropping table %s" % table)
    try:
        db.doQuery("drop table %s" % table)
    except Exception, e:
        db.rollback()
        raise
    

def clear(db):
    for t in ["listcache","quotecache","listcachetables"]:
        dropTable(db,t)
    for t, in db.doQuery("SELECT tablename FROM pg_tables WHERE tablename like 'listcachetable_%'"):
        dropTable(db,t)
    db.commit()

if  __name__ == '__main__':
    import dbtoolkit, config
    import psycopg2 as driver

    cnf = config.Configuration(driver=driver, username="proxy", password='bakkiePleuah', database="proxy", host="localhost", keywordargs=True)
    db = dbtoolkit.amcatDB(cnf)
    clear(db)
