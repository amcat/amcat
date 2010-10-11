from functools import partial
from enum import Enum
import toolkit

levels = Enum(ciritical=1, error=2, warning=3, notice=4, info=5, debug=6)

class Logger(object):

    def __init__(self, db, application=None, defaultlevel=levels.info):
        self.db = db
        self.application = application
        self.defaultlevel = levels.get(defaultlevel)

        self.info = partial(self.log, level=levels.info)
        self.debug = partial(self.log, level=levels.debug)
        self.notice = partial(self.log, level=levels.notice)
        self.warning = partial(self.log, level=levels.warning)
        self.error = partial(self.log, level=levels.error)


    def log(self, message, application=None, level=None):
        try:
            if not level: level=self.defaultlevel
            if not level: raise Exception("No level specified and no default level given!")
            level = levels.get(level)
            
            if not application: application = self.application
            if not application: raise Exception("No application specified and no default application given!")
            
            if len(message) > 4990:
                message = message[:4990] + "..."
            self.db.insert("log", dict(level=level.value, application=application, message=message))
            self.db.commit()
            toolkit.warn( "[%s] %s" % (application, message))
        except Exception, e:
            import traceback
            traceback.print_exc()
            
            toolkit.warn( "[%s] %s generated error: \n%s" % (application, message, e))

#compile daily log reports and mail to subscribed users
def send_reports(db):
    #get subscriptions
    ids = db.doQuery("select * from log_subscriptions")
    emails = []#[db.users.getUser(a).email for a in ids[0]]
    levels = dict(db.doQuery("select * from loglevels"))
    header = "The news for today: \n\n"
    #send mails
    for (id, level, last), email in zip(ids, emails):
        logs = getLogs(db, level, last)
        if logs:
            msg = "\n".join(["%s (%s) %s: %s" % (toolkit.writeDateTime(a[5]), levels[a[2]], a[1], a[3]) for a in logs])
            sendmail.sendmail(email, "log report %d - %d" % (last, logs[-1][0]), header + msg)
            #update last reported id: (1=1 because where clause is not optional)
            last = logs[-1][0]
            db.update("log_subscriptions", where='1=1', newvals=dict(reported_msgid=`last`))
            db.conn.commit()
        else:
            #nothing to report
            pass

def getLogs(db, maxLevel, lastId):
    return db.doQuery("select * from log where msgid >" + `lastId` + " and level <= " + `maxLevel`)

def log(db, message, application, level):
    Logger(db).log(message, application, level)

info = partial(log, level=levels.info)
debug = partial(log, level=levels.debug)
notice = partial(log, level=levels.notice)
warning = partial(log, level=levels.warning)
error = partial(log, level=levels.error)

if __name__ == '__main__':
    import dbtoolkit, sendmail
    
    db = dbtoolkit.amcatDB()
    info(db, "Dit is een test", "draft")
    #send_reports(db)
    #l = Logger(db, "TEST_LOG", 6)
    #l.log("test1")
    #l.warning("testwarning")
    #l.error("testerrpr2")
    #error(db, "testerror", "TEST_LOG2")
