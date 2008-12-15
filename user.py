class Users(object):
    def __init__(self, db):
        self.db = db
        self.byid, self.byname = {}, {}
        SQL = "select username, userid from users"
        for un, uid in db.doQuery(SQL):
            u = User(db, uid, un)
            self.byid[uid] = u
            self.byname[un] = u
    def getUser(self, userid):
        return self.byid[userid]
    def getByName(self, username):
        return self.byname[username]


class User(object):
    def __init__(self, db, id, username = None):
        self.db = db
        self.id = id
        self.username = username
    def getUsername(self):
        if not self.username:
            self.username = self.db.getValue("select username from users where userid = %i" % self.id)
        return self.username
    def idname(self):
        return "%i - %s" % (self.id, self.username)
