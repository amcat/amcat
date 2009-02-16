from toolkit import cached

class Project(object):
    def __init__(self, db, id):
        self.db = db
        self.id = id

    def _getFields(self):
        if self._field: return
        SQL = "select name, ownerid, description FROM projects WHERE projectid=%i" % self.id
        self._name, ownerid, self._description = self.db.doQuery(SQL)[0]
        self._owner = self.db.users.getUser(ownerid)
        self._field = True
    _field = False

    @property
    def name(self):
        self._getFields()
        return self._name

    @property
    def owner(self):
        self._getFields()
        return self._owner

    def href(self):
        return '<a href="projectDetails?projectid=%i">%i - %s</a>' % (self.id, self.id, self.name)
        
    #@cached
    @property
    def batches(self):
        data = self.db.doQuery("""SELECT b.batchid
                     FROM batches AS b
                     WHERE b.projectid = %d""" % self.id, colnames=0)
        return [row[0] for row in data]
