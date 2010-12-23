###########################################################################
#          (C) Vrije Universiteit, Amsterdam (the Netherlands)            #
#                                                                         #
# This file is part of AmCAT - The Amsterdam Content Analysis Toolkit     #
#                                                                         #
# AmCAT is free software: you can redistribute it and/or modify it under  #
# the terms of the GNU Affero General Public License as published by the  #
# Free Software Foundation, either version 3 of the License, or (at your  #
# option) any later version.                                              #
#                                                                         #
# AmCAT is distributed in the hope that it will be useful, but WITHOUT    #
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or   #
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public     #
# License for more details.                                               #
#                                                                         #
# You should have received a copy of the GNU Affero General Public        #
# License along with AmCAT.  If not, see <http://www.gnu.org/licenses/>.  #
###########################################################################

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
