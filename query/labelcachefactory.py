import psycopg2 as driver
import idlabel

class LabelCacheFactory(object):
    def __init__(self, db):
        self.db = db
        self.concept2id = None # conceptstr : labelcacheid
        self.labelcaches = {} # labelcacheid : {id : label}
    def get(self, concept, value):
        if self.concept2id is None:
            self.concept2id = self.querydict("select concept, conceptid from labels_concepts limit 10")
        conceptid = self.concept2id.get(concept)
        if conceptid is not None:
            if conceptid not in self.labelcaches:
                self.labelcaches[conceptid] = self.querydict("select id, label from labels where conceptid=%i" % conceptid)
            lbl = self.labelcaches[conceptid].get(value)
            if lbl: return idlabel.IDLabel(value, lbl)
        return idlabel.IDLabel(value,"CONCEPT %s ID %i" % (concept, value))
    def querydict(self, sql):
        with self.db.cursor() as c:
            c.execute(sql)
            return dict(c.fetchall())
    
def getPostgresLabelCacheFactory():
    db = driver.connect(user="proxy",password='bakkiePleuah', database='proxy', host='localhost')
    return LabelCacheFactory(db)


if __name__ == '__main__':
    lcf = getPostgresLabelCacheFactory()
    print lcf.get("source",4)
