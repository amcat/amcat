import user, toolkit
from toolkit import cached

class Index(object):

    def __init__(self, db, id):
        self.db = db
        self.id = id
        
    def _getFields(self):
        SQL = """select name, storedresultid, owner_userid, projectid, directory from indices
              where indexid=%i""" % self.id
        if self._fields: return
        self._name, self._storedresultid, self._ownerid, self._projectid, self._directory = self.db.doQuery(SQL)[0]
        
        self._fields = True
    _fields = False

    @property
    def name(self):
        self._getFields()
        return self._name

    @property
    def storedresultid(self):
        self._getFields()
        return self._storedresultid