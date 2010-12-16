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

import idlabel
import logging; log = logging.getLogger(__name__)

class LabelCacheFactory(object):
    def __init__(self, db):
        self.db = db
        self.concept2id = None # {conceptstr : labelcacheid}
        self.labelcaches = {} # {labelcacheid : {id : label}}
    def get(self, concept, value):
        if self.db is None: return idlabel.IDLabel(value,"CONCEPT %s ID %i" % (concept, value))
        if self.concept2id is None:
            self.concept2id = self.querydict("select concept, conceptid from labels_concepts")
        conceptid = self.concept2id.get(concept)
        if conceptid is not None:
            if conceptid not in self.labelcaches:
                self.labelcaches[conceptid] = self.querydict("select id, label from labels where conceptid=%i" % conceptid)
            lbl = self.labelcaches[conceptid].get(value)
            if lbl: return idlabel.IDLabel(value, lbl)
            log.warn("conceptid not found in cache db")
        return idlabel.IDLabel(value,"CONCEPT %s ID %i" % (concept, value))
    def querydict(self, sql):
        with self.db.cursor() as c:
            c.execute(sql)
            return dict(c.fetchall())
    
def getPostgresLabelCacheFactory():
    import config as amcat_config
    import dbtoolkit, psycopg2
    cnf = amcat_config.Configuration(driver=psycopg2, username="proxy", password='bakkiePleuah', database="proxy", host="localhost", keywordargs=True)
    db = dbtoolkit.amcatDB(cnf)
    return LabelCacheFactory(db)


if __name__ == '__main__':
    lcf = getPostgresLabelCacheFactory()
    print lcf.get("source",4)
