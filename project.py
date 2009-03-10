from toolkit import cached
import user, permissions


def projects(db, userid, own=1):
    if own:
        sql = """
            SELECT p.projectid
            FROM projects AS p
            INNER JOIN permissions_projects_users as ppu
                ON ppu.projectid = p.projectid
            WHERE ppu.userid = %d
            ORDER BY p.projectid DESC
            """ % userid
    else: # all projects
        sql = """
            SELECT DISTINCT p.projectid
            FROM projects AS p
            LEFT JOIN permissions_projects_users as ppu
                ON ppu.projectid = p.projectid
            INNER JOIN project_visibility AS pv
                ON p.projectid = pv.projectid
            WHERE (ppu.userid = %d OR pv.visibility > 1)
            ORDER BY p.projectid DESC
            """ % userid
    data = db.doQuery(sql, colnames=0)
    for row in data:
        yield Project(db, row[0])


class Project(object):
    def __init__(self, db, id):
        self.db = db
        self.id = id

    def _getFields(self):
        if self._field: return
        SQL = "select name, ownerid, description, insertdate, insertuserid FROM projects WHERE projectid=%i" % self.id
        self._name, ownerid, self._description, self._insertDate, insertid = self.db.doQuery(SQL)[0]
        #self._owner = self.db.users.getUser(ownerid)
        self._insertUser = self.db.users.getUser(insertid)
        self._field = True
    _field = False

    @property
    def name(self):
        self._getFields()
        return self._name
    
    @property
    def insertDate(self):
        self._getFields()
        return self._insertDate

    @property
    def insertUser(self):
        self._getFields()
        return self._insertUser

    @property
    def description(self):
        self._getFields()
        return self._description

    # @property
    # def owner(self):
        # self._getFields()
        # return self._owner

    @property
    def href(self):
        return '<a href="projectDetails?projectid=%i">%i - %s</a>' % (self.id, self.id, self.name)
        
    #@cached
    @property
    def batches(self):
        data = self.db.doQuery("""SELECT b.batchid
                     FROM batches AS b
                     WHERE b.projectid = %d""" % self.id, colnames=0)
        return [row[0] for row in data]

    @property
    def users(self):
        return user.users(self.db, self.id)
            
    @property
    def visibility(self):
        return permissions.projectVisibility(self.db, self.id)
        